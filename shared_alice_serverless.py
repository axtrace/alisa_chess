"""Опциональная точка входа тестового навыка с fail-closed авторизацией общего режима."""

import os

from logging_config import setup_logging
from metrics import measure_skill_request
from shared_chess.replies import inline_state

setup_logging()


def handler(event, context):
    from shared_chess.deadline import budget

    with budget(3.5), measure_skill_request('pilot'):
        return _handle(event, context)


def _handle(event, context):
    user = event.get('state', {}).get('user', {})
    enabled = os.environ.get('SHARED_GAMES_ENABLED', '').lower() == 'true'
    # Existing users stay on the current handler until explicitly enabled and linked.
    if not enabled and not user.get('game_ref'):
        from alice_serverless import handler as legacy

        return legacy(event, context)
    session = event.get('session', {})
    session_state = event.get('state', {}).get('session', {})
    previous = session_state.get('previous_response') or {}
    request = event.get('request', {})
    repeats = 'YANDEX.REPEAT' in request.get('nlu', {}).get('intents', {}) or request.get(
        'command', ''
    ).strip().lower() in ('повтори', 'повторить')
    duplicate = session_state.get('last_message_id') is not None and session_state['last_message_id'] == session.get(
        'message_id'
    )
    if previous.get('kind') == 'inline' and (repeats or duplicate):
        # Reply replay grants no game access and must work during a storage outage.
        return {
            'version': '1.0',
            'session': session,
            'response': previous['response'],
            'user_state_update': user,
            'session_state': {'last_message_id': session.get('message_id'), 'previous_response': previous},
        }
    access_token = (session.get('user') or {}).get('access_token', '')
    try:
        mode = os.environ.get('SHARED_ALICE_AUTH', 'linked_token')
        owner = None
        if mode == 'dialogs_iam':
            from shared_chess.dialogs_identity import dialogs_owner

            owner = dialogs_owner(event, context)
            if owner and request.get('command', '').strip().lower() == 'код тестера':
                response, state = inline_state(session.get('message_id'), 'Код тестера: ' + owner)
                return {
                    'version': '1.0',
                    'session': session,
                    'response': response,
                    'user_state_update': user,
                    'session_state': state,
                }
            if not owner or owner != os.environ.get('SHARED_DIALOGS_ALLOWED_OWNER'):
                if user.get('game_ref'):
                    raise ValueError('Shared player is not enabled')
                from alice_serverless import handler as legacy

                return legacy(event, context)
        elif mode == 'linked_token':
            if not access_token and not user.get('game_ref'):
                from alice_serverless import handler as legacy

                return legacy(event, context)
        else:
            raise ValueError('Unknown shared skill authorization mode')
        from shared_chess.alice import SharedAlice
        from shared_chess.runtime import services

        _, service, auth = services()
        if mode == 'linked_token':
            owner = auth.authenticate(access_token, 'skill')['owner']
        return SharedAlice(service, auth).handle(event, owner)
    except Exception:
        response, state = inline_state(
            session.get('message_id'), 'Общая партия временно недоступна. Позиция сохранена.'
        )
        return {
            'version': '1.0',
            'session': session,
            'response': response,
            'user_state_update': user,
            'session_state': state,
        }
