import logging
import config

from alice_scripts import Request

from alice_chess import AliceChess
from game import Game

if len(logging.getLogger().handlers) > 0:
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

    req = Request(event)
    alice_chess = AliceChess(Game.parse_and_build_game(state), req)
    response = alice_chess.process_request()
    return response
