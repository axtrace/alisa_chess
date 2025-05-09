import chess
import chess.pgn
import requests
import os
from typing import Optional

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
        if 'board_state' in game_state:
            self.board = chess.Board(game_state['board_state'])
        else:
            self.board = chess.Board()
        self.attempts = game_state.get('attempts', 0)
        self.skill_level = game_state.get('skill_level', skill_level)
        self.time_level = game_state.get('time_level', time_level)
        self.winner = game_state.get('winner', '')
        self.skill_state = game_state.get('skill_state', 'INITIATED')
        self.prev_skill_state = game_state.get('prev_skill_state', '')
        self.user_color = game_state.get('user_color', '')
        self._needs_promotion = game_state.get('needs_promotion', False)
 

    def get_user_color(self):
        return self.user_color

    def set_user_color(self, user_color):
        self.user_color = user_color
        print(f"Установлен user_color: {self.user_color}")

    def get_skill_state(self):
        return self.skill_state

    def set_skill_state(self, skill_state):
        """Устанавливает новое состояние, сохраняя предыдущее."""
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

    def get_attempts(self):
        return self.attempts

    def user_move(self, move_san):
        try:
            print(f"Game.user_move. Запрос на ход: {move_san}, доска {self.board.fen()}")
            self.attempts += 1
            self.board.push_san(move_san)
            print(f"Game.user_move. Ход сделан: {move_san}, доска {self.board.fen()}")
        except Exception as e:
            print(f"Game.user_move. Ошибка при ходе {move_san}: {e}")
            return None

    def comp_move(self):
        self.attempts += 1
        # Get the best move from the API
        best_move = self.engine.get_best_move(self.board.fen(), self.skill_level)
        if best_move:
            move = chess.Move.from_uci(best_move)
            san = self.board.san(move)  # Получаем SAN до push
            self.board.push(move)
            return san
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
        self.board = chess.Board()

    def serialize_state(self):
        """Сериализует состояние игры в строку."""
        state = {
            'board_state': self.board.fen(),
            'skill_state': self.skill_state,
            'prev_skill_state': self.prev_skill_state,
            'user_color': self.user_color,
            'attempts': self.attempts,
            'current_turn': 'White' if self.board.turn == chess.WHITE else 'Black',
            'time_level': self.time_level,
            'skill_level': self.skill_level,
            'needs_promotion': self._needs_promotion
        }
        return state


    def check_promotion(self):
        """Проверяет, требуется ли превращение пешки."""
        if not self.board.move_stack:
            self._needs_promotion = False
            return False
            
        last_move = self.board.move_stack[-1]
        if not last_move:
            self._needs_promotion = False
            return False
            
        # Проверяем, является ли последний ход ходом пешки
        piece = self.board.piece_at(last_move.to_square)
        if not piece or piece.piece_type != chess.PAWN:
            self._needs_promotion = False
            return False
            
        # Проверяем, достигла ли пешка последней горизонтали
        rank = chess.square_rank(last_move.to_square)
        self._needs_promotion = (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0)
        return self._needs_promotion

    def promote_pawn(self, promotion_piece):
        """Превращает пешку в указанную фигуру."""
        if not self._needs_promotion:
            return False
            
        last_move = self.board.move_stack[-1]
        if not last_move:
            return False
            
        # Создаем новый ход с превращением
        promotion_move = chess.Move(
            from_square=last_move.from_square,
            to_square=last_move.to_square,
            promotion=promotion_piece
        )
        
        # Отменяем последний ход
        self.board.pop()
        
        # Делаем ход с превращением
        self.board.push(promotion_move)
        self._needs_promotion = False
        return True

    def get_last_move(self):
        """Возвращает последний ход в формате SAN."""
        if not self.board.move_stack:
            return None
        last_move = self.board.move_stack[-1]
        return self.board.san(last_move)

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

    def is_promotion(self):
        """Проверяет, требуется ли превращение пешки."""
        return self.check_promotion()
