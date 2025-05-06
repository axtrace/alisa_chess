from alice_chess import AliceChess
from game import Game
from chess import Board


def handler(event, context):
    """Обработчик запросов от Алисы."""
    try:
        # Инициализируем игру
        game = Game(board=Board())
        
        # Обрабатываем запрос
        alice = AliceChess(game)
        response = alice.handle_request(event)
        
        return {
            'statusCode': 200,
            'body': response
        }
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'text': 'Произошла ошибка при обработке запроса',
                'tts': 'Произошла ошибка при обработке запроса',
                'end_session': True
            }
        }
