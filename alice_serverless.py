from alice_chess import AliceChess
from game import Game
from chess import Board


def handler(event, context):
    """Обработчик запросов от Алисы."""
    try:
        # Восстанавливаем состояние игры из session_state или создаем новую
        if 'state' in event and 'session' in event['state'] and 'game_state' in event['state']['session']:
            game = Game.parse_and_build_game(event['state']['session']['game_state'])
        else:
            game = Game(board=Board())
        
        # Обрабатываем запрос
        alice = AliceChess(game)
        response = alice.handle_request(event)
        
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'text': response,
                'type': 'SimpleUtterance',
                'end_session': False
            },
            'session_state': {
                'game_state': game.serialize_state()
            }
        }
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            'version': '1.0',
            'session': event['session'],
            'response': {
                'text': 'Произошла ошибка при обработке запроса',
                'type': 'SimpleUtterance',
                'tts': 'Произошла ошибка при обработке запроса',
                'end_session': True
            }
        }
