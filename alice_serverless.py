from alice_chess import AliceChess
from game import Game
from chess import Board


def handler(event, context):
    """Обработчик запросов от Алисы."""
    try:
        print(f"Входящий запрос: {event}")
        
        # Восстанавливаем состояние игры из user_state или создаем новую
        if 'state' in event and 'user' in event['state'] and 'game_state' in event['state']['user']:
            print(f"Восстанавливаем состояние из: {event['state']['user']['game_state']}")
            game = Game.parse_and_build_game(event['state']['user']['game_state'])
            print(f"Состояние восстановлено: {game.serialize_state()}")
        else:
            print("Создаем новую игру")
            game = Game(board=Board())
            
        # Обрабатываем запрос
        alice = AliceChess(game)
        response = alice.handle_request(event)
        
        # Сохраняем состояние
        game_state = game.serialize_state()
        print(f"Сохраняем состояние: {game_state}")
        
        return {
            'version': '1.0',
            'session': event['session'],
            'response': response,
            'user_state_update': {
                'game_state': game_state
            }
        }
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'tts': 'Произошла ошибка при обработке запроса',
                'end_session': True
            }
        }
