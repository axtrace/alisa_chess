import chess.engine
import chess.pgn


class Game(object):
    """
    Class for chess game
    """

    def __init__(self):
        self.engine_path = "/usr/games/stockfish"
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.time_level = 0.1  # default

    def start_game(self, turn='white'):
        self.board = chess.Board()

    def user_move(self, move_san):
        self.board.push_san(move_san)

    def comp_move(self):
        result = self.engine.play(self.board,
                                  chess.engine.Limit(time=self.time_level))
        # define the best comp move from engine
        comp_move = self.board.san(result.move)

        # make it on the board
        self.board.push(result.move)
        return comp_move

    def is_game_over(self):
        return self.board.is_game_over()

    def quit(self):
        self.engine.quit()

    def is_move_legal(self, move, board):
        try:
            return board.parse_san(move) in board.legal_moves
        except ValueError:
            return False
        except Exception:
            raise (Exception)

    def change_time_level(self, time_level):
        if 1 < time_level < 10:
            self.time_level = 0.1 * time_level
