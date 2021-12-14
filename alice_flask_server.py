import sys

import chess.pgn
from alice_scripts import Skill, request

import config
from alice_chess import AliceChess
from game import Game

skill = Skill(__name__)


@skill.script
def run_script():
    path_index = 'win' if 'win' in str(sys.platform) else 'nix'
    game = Game(config.engine_path[path_index], chess.Board())
    alice_chess = AliceChess(game, request)
    yield from alice_chess.process_request()


if __name__ == "__main__":
    cur_host = config.HOST_IP
    port = 5000

    skill.run(host=cur_host, port=5000, ssl_context='adhoc', debug=False)
