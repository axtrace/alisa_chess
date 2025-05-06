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
    
    # Восстанавливаем состояние из сессии
    if 'state' in event.get('session', {}):
        game.restore_state(event['session']['state'])
    
    # Обрабатываем запрос
    alice = AliceChess(game, event)
    response = alice.process_request()
    
    # Сохраняем состояние в сессию
    if 'session' in event:
        event['session']['state'] = game.save_state()
    
    return response
