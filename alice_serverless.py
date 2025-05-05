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


def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    print("Incoming event:", event)
    
    if 'state' in event and 'session' in event['state']:
        state = event['state']['session']
    elif 'state' in event and 'application' in event['state']:
        state = event['state']['application']
    else:
        state = {}

    req = RequestAdapter(event)
    alice_chess = AliceChess(Game.parse_and_build_game(state), req)
    response = next(alice_chess.processRequest())
    result = {
        'version': event['version'],
        'session': event['session'],
        'response': response,
        'session_state': alice_chess.get_session_state(),
    }
    print("Outgoing response:", result)
    return result
