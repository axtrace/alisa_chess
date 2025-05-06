from alice_chess import AliceChess
from game import Game
from chess import Board


def handler(event, context):
    """Обработчик запросов к навыку."""
    try:
        # Инициализируем игру
        game = Game()
        
        # Восстанавливаем состояние из user_state
        if 'state' in event and 'user' in event['state']:
            game.restore_state(event['state']['user'])
        
        # Обрабатываем запрос
        response = game.process_request(event)
        
        # Сохраняем состояние в user_state_update
        return {
            'version': event.get('version', '1.0'),
            'session': event['session'],
            'response': {
                'text': response['text'],
                'tts': response['tts'],
                'end_session': response['end_session']
            },
            'user_state_update': game.serialize_state()
        }
        
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            'version': event.get('version', '1.0'),
            'session': event['session'],
            'response': {
                'text': 'Произошла ошибка. Попробуйте еще раз.',
                'tts': 'Произошла ошибка. Попробуйте еще раз.',
                'end_session': False
            },
            'user_state_update': None
        }
