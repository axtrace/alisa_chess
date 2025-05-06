from alice_chess import AliceChess
from game import Game
from chess import Board


class RequestAdapter:
    def __init__(self, event):
        self.event = event
        self.request = event.get('request', {})

    def __getitem__(self, key):
        if key == 'request':
            return self.request
        return self.request.get(key, '')

    def get(self, key, default=None):
        if key == 'request':
            return self.request
        return self.request.get(key, default)


def handler(event, context):
    """Обработчик запросов к навыку."""
    print(f"Received event: {event}")
    
    # Инициализируем игру
    game = Game(board=Board())
    
    # Восстанавливаем состояние из user state
    if 'state' in event and 'user' in event['state']:
        game.restore_state(event['state']['user'])
    
    # Обрабатываем запрос
    alice = AliceChess(game, event)
    response = alice.process_request()
    
    # Формируем ответ в формате Яндекс Диалогов
    return {
        'version': '1.0',
        'session': event['session'],
        'response': {
            'text': response['text'],
            'tts': response['tts'],
            'end_session': response['end_session']
        },
        'state': {
            'session': {},
            'user': game.serialize_state(),
            'application': {}
        }
    }
