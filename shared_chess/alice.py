"""Адаптер общего режима: owner получает из проверенной сессии, не user_id JSON."""

import hashlib
import re
import uuid

from alice_state import player_state, player_state_update
from position_query import position_query
from request_validators.intent_validator import IntentValidator
from shared_chess.replies import inline_state, resolve_reply
from shared_chess.repository import encode
from shared_chess.service import ServiceError


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
            return self._envelope(event['session'], response, player_state(event), state)
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
        user = dict(player_state(event))
        saved = event.get('state', {}).get('session', {})
        request = event.get('request', {})
        text = request.get('command', '').strip().lower()
        previous = saved.get('previous_response')
        try:
            if saved.get('last_message_id') is not None and saved['last_message_id'] == message_id and previous:
                response = resolve_reply(self.service.repository, owner, context, previous)
                return self._envelope(session, response, user, saved)
            if previous and (
                'YANDEX.REPEAT' in request.get('nlu', {}).get('intents', {}) or text in ('повтори', 'повторить')
            ):
                response = resolve_reply(self.service.repository, owner, context, previous)
                return self._envelope(session, response, user, {**saved, 'last_message_id': message_id})
            operation_id = encode(['alice', context['skill_id'], context['session_id'], message_id])
            entry = self.service.repository.atomic(lambda tx: tx.get('commands', owner, operation_id))
            if entry:
                if entry.get('reply_context', {}).get('input_hash') != request_hash:
                    raise ServiceError('IDEMPOTENCY_KEY_REUSED', 'Номер сообщения уже использован для другого запроса.')
                result = self.service.execute(owner, operation_id, entry['command'], entry.get('reply_context'))
                if result['status'] == 'DONE':
                    reply = result['alice_reply']
                    return self._envelope(
                        session,
                        reply['response'],
                        self._user_state(owner, user),
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
            voice = self.service.voice_snapshot(owner)
            if not voice['game_state'] and user.get('game_ref', {}).get('game_id'):
                raise ServiceError('RESTORE_FAILED', 'Общая партия недоступна. Попробуйте позже.', 503)
            if not voice['game_state'] and user.get('game_state'):
                self.service.import_legacy(owner, user['game_state'])
                voice = self.service.voice_snapshot(owner)
            current = voice['snapshot']
            expected = user.get('game_ref')
            validator = IntentValidator(event)
            reading = (
                position_query(request)
                or not text
                or validator.validate_help()
                or validator.validate_show_board()
                or validator.validate_whatcanyoudo()
                or text == 'продолжить'
            )
            if (
                expected
                and not reading
                and (
                    expected['game_id'] != current['game_id']
                    or expected['revision'] != current['revision']
                    or expected.get('dialog_revision', voice['dialog_revision']) != voice['dialog_revision']
                )
            ):
                raise ServiceError('STALE_REVISION', 'Позиция изменилась на другом устройстве. Скажите «покажи доску».')
            command = {
                'request_id': str(uuid.uuid5(uuid.NAMESPACE_URL, operation_id)),
                'game_id': current['game_id'],
                'expected_revision': current['revision'],
                'type': 'voice',
                'payload': {
                    'dialog_revision': voice['dialog_revision'],
                    'request': request,
                    'session': {'message_id': message_id, 'new': session.get('new', False)},
                },
            }
            confirmation = saved.get('confirm')  # Контекст прежней версии пилота.
            if confirmation:
                if (
                    confirmation['game_id'] != current['game_id']
                    or confirmation['revision'] != current['revision']
                    or voice['game_state'].get('skill_state') != 'WAITING_MOVE'
                ):
                    raise ServiceError('STALE_REVISION', 'Позиция изменилась. Повторите действие.')
                command['payload']['legacy_confirmation'] = confirmation['type']
            result = self.service.execute(owner, operation_id, command, context)
            if result['status'] != 'DONE':
                response, state = inline_state(message_id, result['message'])
                return self._envelope(session, response, user, state)
            reply = result['alice_reply']
            user = self._user_state(owner, user)
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

    def _user_state(self, owner, previous):
        voice = self.service.voice_snapshot(owner)
        if not voice['game_state']:
            return previous
        current = voice['snapshot']
        return {
            'game_state': voice['game_state'],
            'game_ref': {
                'game_id': current['game_id'],
                'revision': current['revision'],
                'dialog_revision': voice['dialog_revision'],
            },
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
            **player_state_update(session, user),
            'session_state': state,
        }
