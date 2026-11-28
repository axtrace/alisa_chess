"""Область состояния Диалогов: аккаунт или анонимный экземпляр приложения."""


def has_account(session):
    # Устаревший session.user_id обозначает приложение, а не аккаунт.
    return bool((session.get('user') or {}).get('user_id'))


def player_state(event):
    scope = 'user' if has_account(event.get('session', {})) else 'application'
    return event.get('state', {}).get(scope, {})


def player_state_update(session, state):
    field = 'user_state_update' if has_account(session) else 'application_state'
    return {field: state}
