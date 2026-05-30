"""
Модели для сериализации состояния игры с версионированием.

Структура версий:
- GameStateV1: Текущая схема (совместимость)
- GameStateV2: Новая схема с валидацией
- GameState: Автоматическое определение версии и миграция
"""

import json
import logging
from typing import Any, Optional

import chess
from pydantic import BaseModel, Field, field_validator

from skill_state import SkillState


class GameStateV1(BaseModel):
    """Схема V1 - текущая структура состояния игры."""

    board_state: str = Field(default=chess.STARTING_FEN, description='FEN-строка текущей позиции')
    prev_board_state: str = Field(default='', description='FEN-строка предыдущей позиции')
    skill_state: str = Field(default='', description='Текущее состояние навыка')
    prev_skill_state: str = Field(default='', description='Предыдущее состояние навыка')
    user_color: str = Field(default='', description="Цвет игрока ('white' или 'black')")
    last_move: str = Field(default='', description='Последний ход в SAN-нотации')
    skill_level: int = Field(default=1, ge=1, le=20, description='Уровень сложности (1-20)')
    time_level: float = Field(default=0.1, ge=0.01, le=5.0, description='Время на ход в секундах')

    @field_validator('board_state')
    @classmethod
    def validate_board_state(cls, v):
        """Проверяет корректность FEN-строки."""
        if v and v != chess.STARTING_FEN:
            try:
                chess.Board(v)
            except ValueError as e:
                raise ValueError(f'Некорректная FEN-строка: {v}') from e
        return v

    @field_validator('skill_state')
    @classmethod
    def validate_skill_state(cls, v):
        """Проверяет корректность состояния навыка."""
        if v and v.upper() not in SkillState.__members__:
            raise ValueError(f'Некорректное состояние навыка: {v}')
        return v.upper() if v else v

    @field_validator('user_color')
    @classmethod
    def validate_user_color(cls, v):
        """Проверяет корректность цвета игрока (case-insensitive)."""
        if v and v.upper() not in ('WHITE', 'BLACK'):
            raise ValueError(f'Некорректный цвет игрока: {v}')
        return v.upper() if v else v


class GameStateV2(BaseModel):
    """Схема V2 - улучшенная структура с дополнительными полями."""

    _version: int = 2

    board_state: str = Field(default=chess.STARTING_FEN, description='FEN-строка текущей позиции')
    prev_board_state: str = Field(default='', description='FEN-строка предыдущей позиции')
    skill_state: SkillState = Field(default=SkillState.INITIATED, description='Текущее состояние навыка')
    prev_skill_state: SkillState = Field(default=SkillState.INITIATED, description='Предыдущее состояние навыка')
    user_color: str = Field(default='', description="Цвет игрока ('white' или 'black')")
    last_move: str = Field(default='', description='Последний ход в SAN-нотации')
    skill_level: int = Field(default=1, ge=1, le=20, description='Уровень сложности (1-20)')
    time_level: float = Field(default=0.1, ge=0.01, le=5.0, description='Время на ход в секундах')
    move_count: int = Field(default=0, ge=0, description='Количество сделанных ходов')
    game_start_time: Optional[str] = Field(default=None, description='Время начала игры (ISO формат)')

    @field_validator('board_state')
    @classmethod
    def validate_board_state(cls, v):
        """Проверяет корректность FEN-строки."""
        if v and v != chess.STARTING_FEN:
            try:
                chess.Board(v)
            except ValueError as e:
                raise ValueError(f'Некорректная FEN-строка: {v}') from e
        return v

    @field_validator('user_color')
    @classmethod
    def validate_user_color(cls, v):
        """Проверяет корректность цвета игрока (case-insensitive)."""
        if v and v.upper() not in ('WHITE', 'BLACK'):
            raise ValueError(f'Некорректный цвет игрока: {v}')
        return v.upper() if v else v


class GameState(BaseModel):
    """Автоматическое определение версии состояния и миграция."""

    version: int = Field(default=2, description='Версия схемы состояния')
    data: GameStateV2 = Field(description='Данные состояния игры')

    @classmethod
    def from_dict(cls, state_dict: dict[str, Any]) -> 'GameState':
        """Создает GameState из словаря с автоматической миграцией версий."""
        if not state_dict:
            return cls.default()

        # Определяем версию
        version = state_dict.get('_version', 1)  # По умолчанию V1

        if version == 1:
            # Миграция с V1 на V2
            v1_state = GameStateV1(**state_dict)
            v2_data = cls._migrate_v1_to_v2(v1_state)
            return cls(version=2, data=v2_data)
        elif version == 2:
            # Прямое создание V2
            v2_data = GameStateV2(**state_dict)
            return cls(version=2, data=v2_data)
        else:
            raise ValueError(f'Неподдерживаемая версия состояния: {version}')

    @classmethod
    def _migrate_v1_to_v2(cls, v1_state: GameStateV1) -> GameStateV2:
        """Мигрирует состояние с V1 на V2."""

        def _to_skill_state(v: str) -> SkillState:
            if not v:
                return SkillState.INITIATED
            v_upper = v.upper()
            if v_upper in SkillState.__members__:
                return SkillState(v_upper)
            return SkillState.INITIATED

        return GameStateV2(
            board_state=v1_state.board_state,
            prev_board_state=v1_state.prev_board_state,
            skill_state=_to_skill_state(v1_state.skill_state),
            prev_skill_state=_to_skill_state(v1_state.prev_skill_state),
            user_color=v1_state.user_color,
            last_move=v1_state.last_move,
            skill_level=v1_state.skill_level,
            time_level=v1_state.time_level,
            move_count=0,  # Новое поле
            game_start_time=None,  # Новое поле
        )

    @classmethod
    def default(cls) -> 'GameState':
        """Создает состояние по умолчанию."""
        return cls(version=2, data=GameStateV2())

    def to_dict(self) -> dict[str, Any]:
        """Преобразует состояние в словарь для сериализации."""
        return {'_version': self.version, **self.data.model_dump()}

    def to_json(self) -> str:
        """Сериализует состояние в JSON строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'GameState':
        """Десериализует состояние из JSON строки."""
        try:
            state_dict = json.loads(json_str)
            return cls.from_dict(state_dict)
        except (json.JSONDecodeError, ValueError) as e:
            # При ошибке возвращаем состояние по умолчанию
            logger = logging.getLogger(__name__)
            logger.warning(f'Ошибка десериализации состояния: {e}. Возвращаем состояние по умолчанию.')
            return cls.default()


# Утилиты для работы с состоянием
def create_game_state_from_game(game) -> GameState:
    """Создает GameState из объекта Game."""
    return GameState(
        version=2,
        data=GameStateV2(
            board_state=game.board.fen(),
            prev_board_state=game.prev_board,
            skill_state=SkillState(game.skill_state) if game.skill_state else SkillState.INITIATED,
            prev_skill_state=SkillState(game.prev_skill_state) if game.prev_skill_state else SkillState.INITIATED,
            user_color=game.user_color,
            last_move=game.last_move,
            skill_level=game.skill_level,
            time_level=game.time_level,
            move_count=getattr(game, 'move_count', 0),
            game_start_time=getattr(game, 'game_start_time', None),
        ),
    )


def restore_game_from_state(game, game_state: GameState) -> None:
    """Восстанавливает состояние игры из GameState с обработкой ошибок."""
    logger = logging.getLogger(__name__)

    try:
        data = game_state.data

        # Восстанавливаем доску с защитой от некорректных FEN
        if data.board_state:
            try:
                game.board = chess.Board(data.board_state)
                logger.debug(f'Восстановлена доска из FEN: {data.board_state}')
            except ValueError as e:
                logger.warning(f"Некорректная FEN-строка '{data.board_state}': {e}. Создаем новую доску.")
                game.board = chess.Board()
        else:
            game.board = chess.Board()

        # Восстанавливаем остальные поля с валидацией
        game.prev_board = data.prev_board_state or ''

        # Обработка SkillState с защитой от некорректных значений
        try:
            game.skill_state = data.skill_state.value if data.skill_state else ''
        except (AttributeError, ValueError) as e:
            logger.warning(f'Некорректное состояние навыка: {e}. Устанавливаем INITIATED.')
            game.skill_state = SkillState.INITIATED

        try:
            game.prev_skill_state = data.prev_skill_state.value if data.prev_skill_state else ''
        except (AttributeError, ValueError) as e:
            logger.warning(f'Некорректное предыдущее состояние навыка: {e}. Устанавливаем пустую строку.')
            game.prev_skill_state = ''

        # Валидация цвета игрока (case-insensitive)
        if data.user_color and data.user_color.upper() in ('WHITE', 'BLACK'):
            game.user_color = data.user_color.upper()
        else:
            game.user_color = ''

        # Валидация уровня сложности
        if 1 <= data.skill_level <= 20:
            game.skill_level = data.skill_level
        else:
            logger.warning(f'Некорректный уровень сложности: {data.skill_level}. Устанавливаем 1.')
            game.skill_level = 1

        # Валидация времени на ход
        if 0.01 <= data.time_level <= 5.0:
            game.time_level = data.time_level
        else:
            logger.warning(f'Некорректное время на ход: {data.time_level}. Устанавливаем 0.1.')
            game.time_level = 0.1

        game.last_move = data.last_move or ''

        # Новые поля (если есть)
        if hasattr(game, 'move_count'):
            game.move_count = max(0, data.move_count)
        if hasattr(game, 'game_start_time'):
            game.game_start_time = data.game_start_time

        logger.debug('Состояние игры успешно восстановлено')

    except Exception as e:
        logger.error(f'Критическая ошибка при восстановлении состояния: {e}')
        # В случае критической ошибки создаем новую игру
        game.board = chess.Board()
        game.prev_board = ''
        game.skill_state = SkillState.INITIATED
        game.prev_skill_state = ''
        game.user_color = ''
        game.last_move = ''
        game.skill_level = 1
        game.time_level = 0.1
        if hasattr(game, 'move_count'):
            game.move_count = 0
        if hasattr(game, 'game_start_time'):
            game.game_start_time = None
