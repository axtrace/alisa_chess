from alice_scripts import Request

from alice_chess import AliceChess
from game import Game


def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    if 'state' in event and 'session' in event['state']:
        state = event['state']['session']
    elif 'state' in event and 'application' in event['state']:
        state = event['state']['application']
    else:
        state = {}

    if 'request' in event and 'command' in event['request']:
        req = Request(event)
    else:
        req = Request({'request': {'command': ''}})
    alice_chess = AliceChess(Game.parse_and_build_game(state), req)
    response = next(alice_chess.processRequest())
    return {
        'version': event['version'],
        'session': event['session'],
        'response': response,
        'session_state': alice_chess.get_session_state(),
    }
