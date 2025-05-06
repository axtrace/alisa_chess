from alice_chess import AliceChess
from game import Game


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
    # Инициализируем игру
    game = Game()
    
    # Восстанавливаем состояние из сессии
    if 'state' in event and 'session' in event['state']:
        game.deserialize_state(event['state']['session'])
    
    # Создаем обработчик
    alice_chess = AliceChess(game, event)
    
    # Обрабатываем запрос
    response = alice_chess.process_request()
    
    # Сохраняем состояние в сессию
    session_state = game.serialize_state()
    
    return {
        'version': event['version'],
        'session': event['session'],
        'response': response,
        'session_state': session_state
    }
