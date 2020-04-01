import sys
import chess.engine
import chess.pgn

import config


class Game(object):
    """
    Class for chess game
    """

    def __init__(self):
        path_index = 'win' if 'win' in str(sys.platform) else 'nix'
        self.engine_path = config.engine_path[path_index]
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        # self.time_level = 0.1  # default
        self.skill_level = 1  # default
        self.board = chess.Board()
        self.winner = ''

    def user_move(self, move_san):
        self.board.push_san(move_san)

    def comp_move(self):
        result = self.engine.play(self.board, chess.engine.Limit(time=0.1))
        # define the best comp move from engine
        comp_move = self.board.san(result.move)

        # make it on the board
        self.board.push(result.move)
        return comp_move

    def unmake_move(self):
        # unmake the last user move
        # board.pop()  # Unmake the last move
        # define the user was last moved
        pass

    def is_game_over(self):
        return self.board.is_game_over()

    def quit(self):
        self.engine.quit()

    def is_move_legal(self, move):
        try:
            return self.board.parse_san(move) in self.board.legal_moves
        except ValueError:
            return False
        except Exception:
            raise Exception

    def set_skill_level(self, skill_level):
        self.skill_level = int(skill_level)
        if 0 <= int(skill_level) <= 20:
            self.engine.configure({"Skill Level": self.skill_level})

    def get_skill_level(self):
        return self.skill_level

    def who_invert(self, turn):
        if turn == 'Black':
            return 'White'
        elif turn == 'White':
            return 'Black'
        return ''

    def who(self):
        # who's turn now
        player = self.board.turn
        return 'White' if player == chess.WHITE else 'Black'

    def get_board(self):
        return str(self.board).replace(' ', '\t') + '\n'

    def gameover_reason(self):
        # returns a code for reason of game ends

        if self.board.is_checkmate():
            return '#'
        elif self.board.is_stalemate():
            return '='
        elif self.board.is_fivefold_repetition():
            return '5'
        elif self.board.is_insufficient_material():
            return 'insufficient'
        return ''
