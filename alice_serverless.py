from alice_chess import AliceChess

def handler(event, context):
    """Обработчик запросов от Алисы.
    
    Args:
        event: Данные запроса
        context: Контекст выполнения
    """

    try:
        print(f"Входящий запрос: {event}")
            
        # Инициализируем класс для обработки запросов
        alice = AliceChess()
        # Обрабатываем запрос, внутри восстанавливается состояние игры
        response = alice.handle_request(event)
        
        # Сохраняем состояние игры в контекст пользователя, 
        # чтобы восстановить его при следующем запросе
        print(f"Сохраняем состояние: {alice.get_game_state()}")
        
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
        print(f"Error in handler: {str(e)}")
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'tts': 'Произошла ошибка при обработке запроса',
                'text': f'Произошла ошибка при обработке запроса: {str(e)}',
                'end_session': True
            }
        }
