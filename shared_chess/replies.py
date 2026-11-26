"""Полный неизменяемый ответ в БД, короткая ссылка в состоянии Диалогов."""

import hashlib

from game import Game
from shared_chess.repository import encode
from shared_chess.service import ServiceError


def reply_key(context, reply_id):
    return encode([context['skill_id'], context['session_id'], reply_id])


def response_text(result, state):
    text = result['message']
    if state:
        if result['code'] == 'OK':
            text = f'Последний ход: {state.last_move() or "начальная позиция"}. '
        if state.status == 'finished':
            text += f' Партия завершена: {state.result}.'
        elif state.board().is_check():
            text += ' Шах!'
        with Game(game_state=state.legacy_snapshot()) as game:
            text += '\n' + game.get_board()
    return {
        'text': text,
        'tts': result['message']
        if result['code'] != 'OK'
        else (f'Последний ход {state.last_move()}.' if state and state.last_move() else 'Новая партия.'),
        'end_session': bool(state and state.status == 'finished'),
    }


def save_reply_in_transaction(tx, owner, context, result, state, response=None):
    reply_id = hashlib.sha256(encode([context, result['request_id']]).encode()).hexdigest()[:32]
    if response is None:
        response = response_text(result, state)
    tx.put('replies', owner, reply_key(context, reply_id), {'response': response})
    return {'response': response, 'reference': {'version': 1, 'kind': 'ydb_ref', 'reply_id': reply_id}}


def resolve_reply(repository, owner, context, previous):
    if not previous:
        return {'text': 'Пока нечего повторить.', 'tts': 'Пока нечего повторить.', 'end_session': False}
    if previous.get('version') == 1 and previous.get('kind') == 'inline':
        return previous['response']
    if previous.get('version') == 1 and previous.get('kind') == 'ydb_ref':
        row = repository.atomic(lambda tx: tx.get('replies', owner, reply_key(context, previous['reply_id'])))
        if not row:
            raise ServiceError('REPLY_UNAVAILABLE', 'Предыдущая реплика недоступна.', 503)
        return row['response']
    return previous  # Legacy full response, unchanged.


def inline_state(message_id, text):
    response = {'text': text, 'tts': text, 'end_session': False}
    return response, {
        'last_message_id': message_id,
        'previous_response': {'version': 1, 'kind': 'inline', 'response': response},
    }
