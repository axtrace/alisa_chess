from alice_chess import AliceChess
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """Обработчик запросов от Алисы.
    
    Args:
        event: Данные запроса
        context: Контекст выполнения
    """

    try:
        # Инициализируем класс для обработки запросов
        alice = AliceChess()
        # Обрабатываем запрос, внутри восстанавливается состояние игры
        response = alice.handle_request(event)
        
        # Сохраняем состояние игры в контекст пользователя, 
        # чтобы восстановить его при следующем запросе

        return {
            'version': '1.0',
            'session': event['session'],
            'response': response,
            'user_state_update': {
                'game_state': alice.get_game_state()
            },
            "session_state": {
                "previous_response": response
            },
        }
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}") 
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'tts': 'Произошла ошибка при обработке запроса',
                'text': f'Произошла ошибка при обработке запроса: {str(e)}',
                'end_session': True
            }
        }
