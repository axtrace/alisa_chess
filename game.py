import chess
import requests
import os
from typing import Optional
import io
import base64

class ChessEngineAPI:
    def __init__(self, api_key: str = None):
        self.api_url = os.getenv("CHESS_API_URL", "https://alice-chess.ru:8000/bestmove/")
        self.api_key = api_key or os.getenv("CHESS_API_KEY", "")

    def get_best_move(self, fen: str, depth: int = 10) -> Optional[str]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "fen": fen,
            "depth": depth
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("best move")
        except requests.exceptions.RequestException as e:
            print(f"Error getting best move: {e}")
            return None

class Game(object):
    """
    Class for chess game
    """
    def __init__(self, board: chess.Board, skill_level: int = 1, time_level: float = 0.1):
        self.engine = ChessEngineAPI()
        self.board = board
        self.attempts = 0
        self.skill_level = skill_level
        self.time_level = time_level
        self.winner = ''
        self.skill_state = ''
        self.user_color = ''

    def get_user_color(self):
        return self.user_color

    def set_user_color(self, user_color):
        self.user_color = user_color

    def get_skill_state(self):
        return self.skill_state

    def set_skill_state(self, skill_state):
        self.skill_state = skill_state

    def get_attempts(self):
        return self.attempts

    def user_move(self, move_san):
        self.attempts += 1
        self.board.push_san(move_san)

    def comp_move(self):
        self.attempts += 1
        # Get the best move from the API
        best_move = self.engine.get_best_move(self.board.fen(), self.skill_level)
        if best_move:
            move = chess.Move.from_uci(best_move)
            self.board.push(move)
            return self.board.san(move)
        else:
            return None

    def unmake_move(self):
        # unmake the last user move
        return self.board.pop() # Unmake the last move

    # define the user was last moved
    def is_game_over(self):
        return self.board.is_game_over()

    def quit(self):
        pass # API не требует quit

    def is_move_legal(self, move):
        try:
            return self.board.parse_san(move) in self.board.legal_moves
        except ValueError:
            return False

    def set_skill_level(self, skill_level):
        self.skill_level = int(skill_level)

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
        return self.board.unicode() + '\n'

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

    @staticmethod
    def parse_and_build_game(state):
        if state.get("board_state", ""):
            pgn = io.StringIO(base64.b64decode(state['board_state']).decode('utf-8'))
            chess_game = chess.pgn.read_game(pgn)
            board = chess_game.board()
        else:
            board = chess.Board()
        game = Game(board)
        game.set_skill_state(state.get('skill_state', ''))
        game.set_user_color(state.get('user_color', ''))
        game.attempts = state.get('attempts', 0)
        return game

    def serialize_state(self):
        """Serialize game state to string."""
        exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
        return self.board.accept(exporter)
