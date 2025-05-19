import chess
import chess.pgn
import requests
import os
from typing import Optional

class ChessEngineAPI:
    def __init__(self, api_key: str = None):
        self.api_url = os.getenv("CHESS_API_URL", "https://alice-chess.ru:8000/bestmove/")
        self.api_key = api_key or os.getenv("CHESS_API_KEY", "")

    def get_best_move(self, fen: str, depth: int = 10, time: float = 0.1) -> Optional[str]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "fen": fen,
            "depth": depth,
            "time": time
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("best_move")
        except requests.exceptions.RequestException as e:
            print(f"Error getting best move: {e}")
            return None

class Game(object):
    """
    Class for chess game
    """
    def __init__(self, skill_level: int = 1, time_level: float = 0.1, game_state: dict = {}):
        self.engine = ChessEngineAPI()
        self.board = self._init_board(game_state)
        self.prev_board = game_state.get('board_state', '') # запоминаем доску для отмены хода
        self.skill_level = game_state.get('skill_level', skill_level)
        self.time_level = game_state.get('time_level', time_level)
        self.skill_state = game_state.get('skill_state', 'INITIATED')
        self.prev_skill_state = game_state.get('prev_skill_state', '')
        self.user_color = game_state.get('user_color', '')
        self.last_move = game_state.get('last_move', '')
        
    def _init_board(self, game_state):
        if 'board_state' in game_state:
            return chess.Board(game_state['board_state'])
        else:
            return chess.Board()
        
    def undo_move(self):
        if self.prev_board:
            print(f"Game.undo_move. Восстанавливаем доску: {self.prev_board}")  
            self.board = chess.Board(self.prev_board)
            self.prev_board = ''
            return True
        else:
            return False

    def get_user_color(self):
        return self.user_color

    def set_user_color(self, user_color):
        self.user_color = user_color
        print(f"Установлен user_color: {self.user_color}")

    def get_skill_state(self):
        return self.skill_state

    def set_skill_state(self, skill_state):
        """Устанавливает новое состояние, сохраняя предыдущее, отличающееся от нового."""
        if self.skill_state != skill_state:
            self.prev_skill_state = self.skill_state
        self.skill_state = skill_state
        print(f"Установлено состояние: {self.skill_state}. Предыдущее состояние: {self.prev_skill_state}")

    def get_prev_skill_state(self):
        """Возвращает предыдущее состояние."""
        return self.prev_skill_state

    def restore_prev_state(self):
        """Восстанавливает предыдущее состояние."""
        self.skill_state = self.prev_skill_state
        self.prev_skill_state = ''

    def user_move(self, move_san):
        print(f"Game.user_move. Запрос на ход: {move_san}, доска {self.board.fen()}")

        self.board.push_san(move_san)
        print(f"Game.user_move. Ход сделан: {move_san}, доска {self.board.fen()}")

    def comp_move(self):
        # Get the best move from the API
        best_move = self.engine.get_best_move(self.board.fen(), self.skill_level, self.time_level)
        if best_move:
            move = chess.Move.from_uci(best_move)
            san = self.board.san(move)  # Получаем SAN до push
            self.board.push(move)
            self.last_move = san
            return san
        else:
            return None

    def undo_move(self):
        # unmake the last user move
        return self.board.pop() # Unmake the last move

    # define the user was last moved
    def is_game_over(self):
        return self.board.is_game_over()

    def is_move_legal(self, move):
        try:
            return self.board.parse_san(move) in self.board.legal_moves
        except ValueError:
            return False

    def set_skill_level(self, skill_level):
        self.skill_level = int(skill_level)
        if self.skill_level > 17:
            self.time_level = 2.0
        elif self.skill_level > 15:
            self.time_level = 1.0
        elif self.skill_level > 10:
            self.time_level = 0.8
        elif self.skill_level > 7:
            self.time_level = 0.5
        elif self.skill_level > 5:
            self.time_level = 0.3
        else:   
            self.time_level = 0.1
        print(f"Game.set_skill_level. skill_level: {self.skill_level}, time_level: {self.time_level}")
    

    def get_skill_level(self):
        return self.skill_level

    def who(self):
        # who's turn now
        if self.board.turn == chess.WHITE:
            return 'White' 
        return 'Black'

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
    
    def reset_board(self):
        self.prev_board = self.board.fen()
        self.board = chess.Board()
        self.last_move = ''
        self.user_color = ''
        self.prev_skill_state = ''

    def serialize_state(self):
        """Сериализует состояние игры в строку."""
        state = {
            'board_state': self.board.fen(),
            'prev_board_state': self.prev_board,
            'skill_state': self.skill_state,
            'prev_skill_state': self.prev_skill_state,
            'user_color': self.user_color,
            'current_turn': 'WHITE' if self.board.turn == chess.WHITE else 'BLACK',
            'time_level': self.time_level,
            'skill_level': self.skill_level,
            'last_move': self.get_last_move()
        }
        return state

    def get_last_move(self):
        """Возвращает последний ход в формате SAN."""
        return self.last_move
    
    def is_valid_move(self, move_san):
        """Проверяет, является ли ход допустимым."""
        try:
            move = self.board.parse_san(move_san)
            return move in self.board.legal_moves
        except ValueError:
            return False

    def is_checkmate(self):
        """Проверяет, является ли текущая позиция матом."""
        return self.board.is_checkmate()

    def is_stalemate(self):
        """Проверяет, является ли текущая позиция патом."""
        return self.board.is_stalemate()

    def is_check(self):
        """Проверяет, находится ли текущая сторона под шахом."""
        return self.board.is_check()

    def is_insufficient_material(self):
        """Проверяет недостаточность материала для продолжения игры."""
        return self.board.is_insufficient_material()

    def is_fivefold_repetition(self):
        """Проверяет пятикратное повторение позиции."""
        return self.board.is_fivefold_repetition()