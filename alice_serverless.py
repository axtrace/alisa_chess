from alice_chess import AliceChess
from logging_config import (
    setup_logging,
    bind_request_context,
    clear_request_context,
)
from metrics import emit_counter, measure_duration
import logging

setup_logging()
logger = logging.getLogger(__name__)

# Признак холодного старта: модуль импортируется один раз на инстанс контейнера.
_COLD_START_PENDING = True


def _extract_request_ids(event):
    """Безопасно извлекает идентификаторы запроса для контекста логирования."""
    ids = {}
    try:
        session = event.get('session', {}) if isinstance(event, dict) else {}
        if isinstance(session, dict):
            if session.get('session_id'):
                ids['session_id'] = session.get('session_id')
            if session.get('message_id') is not None:
                ids['message_id'] = session.get('message_id')
            if session.get('user_id'):
                ids['user_id'] = session.get('user_id')
            user = session.get('user') or {}
            if isinstance(user, dict) and user.get('user_id'):
                ids['user_id'] = user.get('user_id')
    except Exception:
        pass
    return ids


def handler(event, context):
    """Обработчик запросов от Алисы.

    Args:
        event: Данные запроса
        context: Контекст выполнения
    """

    global _COLD_START_PENDING
    bind_request_context(**_extract_request_ids(event))
    if _COLD_START_PENDING:
        emit_counter('skill.cold_start')
        _COLD_START_PENDING = False
    emit_counter('skill.request')
    alice = None
    try:
        with measure_duration('skill.handler.duration_ms'):
            # Инициализируем класс для обработки запросов с контекстным менеджером
            with AliceChess() as alice:
                # Обрабатываем запрос, внутри восстанавливается состояние игры
                response = alice.handle_request(event)
                session_state = alice.get_session_state() if hasattr(alice, 'get_session_state') else {}
                game_state = alice.get_game_state()

        return {
            'version': '1.0',
            'session': event['session'],
            'response': response,
            'user_state_update': {
                'game_state': game_state
            },
            "session_state": session_state,
        }
    except Exception as e:
        emit_counter('skill.error', tags={'kind': type(e).__name__})
        logger.error(f"Error in handler: {str(e)}")

        # Пытаемся сохранить состояние игры, если оно было инициализировано
        game_state = None
        try:
            if alice is not None:
                game_state = alice.get_game_state()
        except Exception as state_error:
            logger.error(f"Error getting game state: {state_error}")

        error_text = f'Произошла ошибка при обработке запроса: {str(e)}'
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'tts': 'Произошла ошибка при обработке запроса',
                'text': error_text,
                'end_session': True,
            },
            'user_state_update': {
                'game_state': game_state
            } if game_state else {},
            "session_state": {
                "previous_response": {
                    'tts': 'Произошла ошибка при обработке запроса',
                    'text': error_text,
                }
            }
        }
    finally:
        clear_request_context()
