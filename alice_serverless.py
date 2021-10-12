import json
import logging

from alice_scripts import Request

from alice_chess import AliceChess
from game import Game

stockfish_engine_path = "./stockfish"

root_handler = logging.getLogger().handlers[0]
root_handler.setFormatter(logging.Formatter(
    '[%(levelname)s]\t%(name)s\t[%(request_id)s]\t%(message)s\n'
))


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
    alice_chess = AliceChess(Game.parse_and_build_game(stockfish_engine_path, state), req)
    response = next(alice_chess.processRequest())
    return {
        'version': event['version'],
        'session': event['session'],
        'response': response,
        # https://yandex.ru/dev/dialogs/alice/doc/session-persistence.html
        'session_state': alice_chess.get_session_state(),
        # 'application_state': alice_chess.get_session_state(),
    }
