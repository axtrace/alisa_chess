import logging

import chess
import chess.engine
import chess.pgn

from skill_state import SkillState

logger = logging.getLogger(__name__)


class Game:
    """
    Class for chess game
    """

    def __init__(self, skill_level: int = 1, time_level: float = 0.1, game_state: dict = None):
        if game_state is None:
            game_state = {}
        self._engine = None  # Ленивая инициализация

        # Автоматическая миграция состояния при инициализации
        if game_state:
            # Инициализируем дефолтные значения, чтобы поля точно существовали
            self._init_default_state(skill_level, time_level)
            # Если board_state задан, валидируем его строго (тесты ожидают ValueError)
            board_state = game_state.get('board_state')
            if board_state:
                # Может бросить ValueError - это ожидаемое поведение
                self.board = chess.Board(board_state)
            from game_state import GameState

            try:
                game_state_obj = GameState.from_dict(game_state)
                self._restore_from_game_state(game_state_obj)
            except ValueError:
                # Пробрасываем ValueError (некорректный FEN и т.п.)
                raise
            except Exception as e:
                logger.warning(f'Ошибка миграции состояния: {e}. Используем состояние по умолчанию.')
        else:
            self._init_default_state(skill_level, time_level)

    def _init_default_state(self, skill_level: int, time_level: float):
        """Инициализирует состояние по умолчанию."""
        self.board = chess.Board()
        self.prev_board = ''
        self.skill_level = skill_level
        self.time_level = time_level
        self.skill_state = SkillState.INITIATED
        self.prev_skill_state = ''
        self.user_color = ''
        self.last_move = ''
        self.move_count = 0
        self.game_start_time = None

    def _restore_from_game_state(self, game_state):
        """Восстанавливает состояние из GameState."""
        from game_state import restore_game_from_state

        restore_game_from_state(self, game_state)

    @property
    def engine(self):
        """Ленивая инициализация Stockfish engine."""
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci('./stockfish')
            # Конфигурируем уровень сложности при первом запуске
            self._engine.configure({'Skill Level': self.skill_level})
        return self._engine

    def _init_board(self, game_state):
        if 'board_state' in game_state:
            return chess.Board(game_state['board_state'])
        else:
            return chess.Board()

    def _init_prev_board(self, game_state):
        try:
            prev_board = game_state.get('prev_board_state', '')
            if prev_board:
                return chess.Board(prev_board).fen()
            else:
                return self.board.fen()
        except Exception as e:
            logger.error(f'Game._init_prev_board. Ошибка при инициализации prev-доски: {e}')
            return self.board.fen()

    def undo_move(self):
        if self.prev_board:
            self.board = chess.Board(self.prev_board)
            self.prev_board = ''
            return True
        else:
            return False

    def get_user_color(self):
        return self.user_color

    def get_comp_color(self):
        """Возвращает цвет компьютера (противоположный цвету пользователя)."""
        return 'WHITE' if self.user_color == 'BLACK' else 'BLACK'

    def set_user_color(self, user_color):
        self.user_color = user_color

    def get_skill_state(self):
        return self.skill_state

    def set_skill_state(self, skill_state):
        """Устанавливает новое состояние, сохраняя предыдущее, отличающееся от нового."""
        if self.skill_state != skill_state:
            self.prev_skill_state = self.skill_state
        self.skill_state = skill_state

    def get_prev_skill_state(self):
        """Возвращает предыдущее состояние."""
        return self.prev_skill_state

    def restore_prev_state(self):
        """Восстанавливает предыдущее состояние."""
        self.skill_state = self.prev_skill_state
        self.prev_skill_state = ''

    def user_move(self, move_san):
        self.board.push_san(move_san)

    def comp_move(self):
        self.engine.configure({'Skill Level': self.skill_level})
        result = self.engine.play(self.board, chess.engine.Limit(time=self.time_level))
        if result.move:
            san = self.board.san(result.move)
            self.board.push(result.move)
            self.last_move = san
            logger.info(f'Game.comp_move. Ход сделан: {san}, доска {self.board.fen()}')
            return san
        else:
            logger.error('Game.comp_move. Движок не вернул ход')
            return None

    # define the user was last moved
    def is_game_over(self):
        return self.board.is_game_over()

    MIN_SKILL_LEVEL = 1
    MAX_SKILL_LEVEL = 20
    DEFAULT_SKILL_LEVEL = 1

    def set_skill_level(self, skill_level):
        """Безопасно устанавливает уровень сложности Stockfish.

        Принимает значения, приводимые к int. При невалидном входе откатывается
        к DEFAULT_SKILL_LEVEL. Итоговое значение клампится в диапазон
        [MIN_SKILL_LEVEL, MAX_SKILL_LEVEL].
        """
        try:
            parsed_level = int(skill_level)
        except (TypeError, ValueError):
            logger.error(
                f'Game.set_skill_level. Невалидный skill_level={skill_level!r}, '
                f'использую DEFAULT_SKILL_LEVEL={self.DEFAULT_SKILL_LEVEL}'
            )
            parsed_level = self.DEFAULT_SKILL_LEVEL

        clamped_level = max(self.MIN_SKILL_LEVEL, min(self.MAX_SKILL_LEVEL, parsed_level))
        if clamped_level != parsed_level:
            logger.warning(
                f'Game.set_skill_level. skill_level={parsed_level} выходит за диапазон '
                f'[{self.MIN_SKILL_LEVEL}, {self.MAX_SKILL_LEVEL}], скорректирован до {clamped_level}'
            )
        self.skill_level = clamped_level

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
        # Конфигурируем engine только если он уже инициализирован
        if self._engine is not None:
            try:
                self.engine.configure({'Skill Level': self.skill_level})
            except Exception as e:
                logger.error(f'Game.set_skill_level. Ошибка конфигурации движка: {e}')
        logger.info(f'Game.set_skill_level. skill_level: {self.skill_level}, time_level: {self.time_level}')

    def quit(self):
        """Безопасно закрывает Stockfish engine."""
        if self._engine is not None:
            try:
                self._engine.quit()
                self._engine = None
            except Exception as e:
                logger.error(f'Game.quit. Ошибка при закрытии движка: {e}')

    def __enter__(self):
        """Контекстный менеджер для гарантированного закрытия движка."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Гарантированное закрытие движка при выходе из контекста."""
        self.quit()
        return False  # Не подавляем исключения

    def __del__(self):
        """Гарантированное закрытие движка при удалении объекта."""
        self.quit()

    def get_engine_name(self):
        """Возвращает название движка, например 'Stockfish 18'."""
        if self._engine is None:
            return 'Stockfish'
        return self.engine.id.get('name', 'Stockfish')

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
        elif self.board.can_claim_threefold_repetition():
            return '3'
        elif self.board.can_claim_fifty_moves():
            return '50'
        return ''

    def reset_board(self):
        self.board = chess.Board()
        self.prev_board = ''
        self.last_move = ''
        self.user_color = ''
        self.prev_skill_state = ''

    def serialize_state(self):
        """Сериализует состояние игры в словарь (совместимость)."""
        from game_state import create_game_state_from_game

        game_state = create_game_state_from_game(self)
        result = game_state.to_dict()
        # Добавляем поля для обратной совместимости
        result['current_turn'] = 'WHITE' if self.board.turn == chess.WHITE else 'BLACK'
        result['comp_color'] = self.get_comp_color() if self.user_color else ''
        return result

    def serialize_state_v2(self):
        """Сериализует состояние игры с использованием новой схемы."""
        from game_state import create_game_state_from_game

        return create_game_state_from_game(self)

    def get_last_move(self):
        """Возвращает последний ход в формате SAN."""
        return self.last_move

    def is_valid_move(self, move_san):
        """Проверяет, является ли ход допустимым (в формате SAN)."""
        try:
            move = self.board.parse_san(move_san)
            return move in self.board.legal_moves
        except ValueError:
            logger.error(f'Game.is_valid_move. Ошибка при проверке допустимости хода: {move_san}')
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

    def can_claim_threefold_repetition(self):
        """Проверяет, можно ли требовать ничью по троекратному повторению позиции."""
        return self.board.can_claim_threefold_repetition()

    def can_claim_fifty_moves(self):
        """Проверяет, можно ли требовать ничью по правилу 50 ходов."""
        return self.board.can_claim_fifty_moves()
