from alice_chess import AliceChess
from game import Game
from chess import Board


def handler(event, context):
    """Обработчик запросов от Алисы."""
    try:
        # Восстанавливаем состояние игры из user_state или создаем новую
        if 'state' in event and 'user' in event['state'] and 'game_state' in event['state']['user']:
            game = Game.parse_and_build_game(event['state']['user']['game_state'])
        else:
            game = Game(board=Board())

        # Обрабатываем запрос
        alice = AliceChess(game)
        response = alice.handle_request(event)
        
        return {
            'version': '1.0',
            'session': event['session'],
            'response': response,
            'user_state_update': {
                'game_state': alice.get_game_state()
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
