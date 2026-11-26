"""Адаптер общего режима: owner получает из проверенной сессии, не user_id JSON."""

import hashlib
import re
import uuid

from position_query import position_query, position_response
from shared_chess.replies import inline_state, reply_key, resolve_reply
from shared_chess.repository import encode
from shared_chess.service import ServiceError
from shared_chess.state import SharedGameState


class SharedAlice:
    def __init__(self, service, auth):
        self.service, self.auth = service, auth

    def handle(self, event, owner):
        request_hash = hashlib.sha256(encode(event.get('request', {})).encode()).hexdigest()[:32]
        saved = event.get('state', {}).get('session', {})
        if (
            saved.get('last_message_id') == event['session']['message_id']
            and saved.get('request_hash')
            and saved['request_hash'] != request_hash
        ):
            response, state = inline_state(
                event['session']['message_id'], 'Номер сообщения уже использован. Повторите запрос новым сообщением.'
            )
            return self._envelope(event['session'], response, event.get('state', {}).get('user', {}), state)
        result = self._handle(event, owner, request_hash)
        result['session_state']['request_hash'] = request_hash
        return result

    def _handle(self, event, owner, request_hash):
        session = event['session']
        message_id = session['message_id']
        context = {
            'skill_id': session['skill_id'],
            'session_id': session['session_id'],
            'message_id': message_id,
            'input_hash': request_hash,
        }
        user = dict(event.get('state', {}).get('user', {}))
        saved = event.get('state', {}).get('session', {})
        request = event.get('request', {})
        text = request.get('command', '').strip().lower()
        previous = saved.get('previous_response')
        try:
            if saved.get('last_message_id') is not None and saved['last_message_id'] == message_id and previous:
                response = resolve_reply(self.service.repository, owner, context, previous)
                return self._envelope(session, response, user, saved)
            if 'YANDEX.REPEAT' in request.get('nlu', {}).get('intents', {}) or text in ('повтори', 'повторить'):
                response = resolve_reply(self.service.repository, owner, context, previous)
                return self._envelope(
                    session, response, user, {'last_message_id': message_id, 'previous_response': previous}
                )
            operation_id = encode(['alice', context['skill_id'], context['session_id'], message_id])
            entry = self.service.repository.atomic(lambda tx: tx.get('commands', owner, operation_id))
            if entry:
                if entry.get('reply_context', {}).get('input_hash') != request_hash:
                    raise ServiceError('IDEMPOTENCY_KEY_REUSED', 'Номер сообщения уже использован для другого запроса.')
                result = self.service.execute(owner, operation_id, entry['command'], entry.get('reply_context'))
                if result['status'] == 'DONE':
                    reply = result['alice_reply']
                    current = self.service.current(owner)
                    return self._envelope(
                        session,
                        reply['response'],
                        self._user_state(owner, current, user),
                        {'last_message_id': message_id, 'previous_response': reply['reference']},
                    )
                response, state = inline_state(message_id, result['message'])
                return self._envelope(session, response, user, state)
            code = re.search(r'(?:подключить экран|подключи экран).*?(\d{6})', text)
            if code:
                response, state = inline_state(
                    message_id, 'Подключить экран с этим кодом к вашей партии? Скажите «да» или «нет».'
                )
                state['pairing_code'] = code[1]
                return self._envelope(session, response, user, state)
            if saved.get('pairing_code'):
                if text in ('да', 'подтверждаю'):
                    self.auth.confirm_pairing(owner, saved['pairing_code'])
                    message = 'Экран подключён к вашей партии.'
                else:
                    message = 'Подключение отменено.'
                response, state = inline_state(message_id, message)
                return self._envelope(session, response, user, state)
            current = self.service.current(owner)
            if not current['game_id'] and user.get('game_ref'):
                raise ServiceError('RESTORE_FAILED', 'Общая партия недоступна. Попробуйте позже.', 503)
            if not current['game_id'] and user.get('game_state'):
                try:
                    current = self.service.import_legacy(owner, user['game_state'])
                except ValueError:
                    pass  # An unfinished legacy setup is not a ready match.
            expected = user.get('game_ref')
            if text in ('новая игра', 'начать заново', 'сдаюсь', 'сдаться'):
                response, state = inline_state(message_id, 'Подтвердите действие: скажите «да» или «нет».')
                state['confirm'] = {
                    'type': 'new_game' if 'игра' in text or 'заново' in text else 'resign',
                    'game_id': current['game_id'],
                    'revision': current['revision'],
                }
                return self._envelope(session, response, user, state)
            confirmation = saved.get('confirm')
            kind, payload = 'move_text', {'text': request.get('command', '')}
            query = position_query(request)
            if confirmation:
                if text not in ('да', 'подтверждаю'):
                    response, state = inline_state(message_id, 'Действие отменено.')
                    return self._envelope(session, response, user, state)
                if confirmation['game_id'] != current['game_id'] or confirmation['revision'] != current['revision']:
                    raise ServiceError('STALE_REVISION', 'Позиция изменилась. Повторите действие.')
                kind, payload = confirmation['type'], {}
                if kind == 'new_game':
                    payload = {
                        'user_color': current.get('user_color', 'WHITE'),
                        'skill_level': current.get('skill_level', 1),
                    }
            elif text in ('отмени ход', 'отмена хода', 'назад'):
                kind, payload = 'undo', {}
            elif re.fullmatch(r'(?:сложность|уровень)\s+\d{1,2}', text):
                kind, payload = 'set_level', {'skill_level': int(text.split()[-1])}
            elif query or not text or text in ('доска', 'покажи доску', 'продолжить', 'помощь'):
                if not current['game_id']:
                    response, state = inline_state(message_id, 'Начните партию на экране или скажите «новая игра».')
                    return self._envelope(session, response, user, state)
                return self._show_current(session, owner, context, current, query)
            elif expected and (
                expected['game_id'] != current['game_id'] or expected['revision'] != current['revision']
            ):
                raise ServiceError('STALE_REVISION', 'Доска изменилась на другом устройстве. Скажите «покажи доску».')
            command = {
                'request_id': str(uuid.uuid5(uuid.NAMESPACE_URL, operation_id)),
                'game_id': current['game_id'],
                'expected_revision': current['revision'],
                'type': kind,
                'payload': payload,
            }
            result = self.service.execute(owner, operation_id, command, context)
            if result['status'] != 'DONE':
                response, state = inline_state(message_id, result['message'])
                return self._envelope(session, response, user, state)
            reply = result['alice_reply']
            snapshot = result['snapshot']
            user = self._user_state(owner, snapshot, user)
            return self._envelope(
                session,
                reply['response'],
                user,
                {'last_message_id': message_id, 'previous_response': reply['reference']},
            )
        except ServiceError as error:
            response, state = inline_state(message_id, error.message)
            return self._envelope(session, response, user, state)
        except Exception:
            response, state = inline_state(message_id, 'Хранилище временно недоступно. Позиция сохранена.')
            return self._envelope(session, response, user, state)

    def _show_current(self, session, owner, context, current, query):
        from shared_chess.replies import response_text

        record = self.service.repository.atomic(lambda tx: tx.get('games', owner, current['game_id']))
        state = SharedGameState.model_validate(record['state'])
        if query:
            response = position_response(query, state.board(), state.user_color)
        else:
            response = response_text({'code': 'OK', 'message': 'Ваша очередь.'}, state)
        user = {
            'game_state': state.legacy_snapshot(),
            'game_ref': {'game_id': current['game_id'], 'revision': record['revision']},
        }
        reply_id = hashlib.sha256(encode(context).encode()).hexdigest()[:32]
        self.service.repository.atomic(
            lambda tx: tx.put('replies', owner, reply_key(context, reply_id), {'response': response})
        )
        return self._envelope(
            session,
            response,
            user,
            {
                'last_message_id': session['message_id'],
                'previous_response': {'version': 1, 'kind': 'ydb_ref', 'reply_id': reply_id},
            },
        )

    def _user_state(self, owner, snapshot, previous):
        if not snapshot.get('game_id'):
            return previous
        record = self.service.repository.atomic(lambda tx: tx.get('games', owner, snapshot['game_id']))
        return {
            'game_state': SharedGameState.model_validate(record['state']).legacy_snapshot(),
            'game_ref': {'game_id': snapshot['game_id'], 'revision': snapshot['revision']},
        }

    @staticmethod
    def _envelope(session, response, user, state):
        # The compatibility snapshot and pointer each stay within the Dialogs budgets.
        if len(encode(state).encode()) > 1024 or len(encode(user).encode()) > 1024:
            response, state = inline_state(session['message_id'], 'Не удалось сохранить состояние. Попробуйте позже.')
            # Preserve input game data; never silently truncate the user's match.
        return {
            'version': '1.0',
            'session': session,
            'response': response,
            'user_state_update': user,
            'session_state': state,
        }
