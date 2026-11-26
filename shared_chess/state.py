"""Версионированная партия с проверяемой историей и границами отмены."""

from typing import Literal

import chess
from pydantic import BaseModel, ConfigDict, Field, model_validator

from game_state import GameState


class SharedGameState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1
    initial_fen: str = chess.STARTING_FEN
    moves_uci: list[str] = Field(default_factory=list)
    turn_starts: list[int] = Field(default_factory=list)
    user_color: Literal['WHITE', 'BLACK'] = 'WHITE'
    skill_level: int = Field(default=1, ge=1, le=20)
    status: Literal['playing', 'finished'] = 'playing'
    result: str = '*'
    history_complete: bool = True
    legacy_undo_fen: str | None = None
    base_last_move: str = ''

    def board(self):
        board = chess.Board(self.initial_fen)
        if not board.is_valid():
            raise ValueError('Некорректная позиция')
        for uci in self.moves_uci:
            board.push_uci(uci)
        return board

    @model_validator(mode='after')
    def validate_history(self):
        self.board()
        if self.turn_starts != sorted(set(self.turn_starts)):
            raise ValueError('Границы ходов должны возрастать')
        if any(i < 0 or i >= len(self.moves_uci) for i in self.turn_starts):
            raise ValueError('Граница хода вне истории')
        if self.legacy_undo_fen:
            previous = chess.Board(self.legacy_undo_fen)
            color = self.user_color == 'WHITE'
            if not previous.is_valid() or previous.turn != color:
                raise ValueError('Непригодная позиция для отмены импорта')
        return self

    @classmethod
    def import_legacy(cls, snapshot):
        data = GameState.from_dict(snapshot).data
        if data.user_color not in ('WHITE', 'BLACK'):
            raise ValueError('Сначала завершите выбор цвета в голосовом навыке')
        undo = data.prev_board_state or None
        if undo:
            try:
                previous = chess.Board(undo)
                if not previous.is_valid() or previous.turn != (data.user_color == 'WHITE'):
                    undo = None
            except ValueError:
                undo = None
        state = cls(
            initial_fen=data.board_state,
            user_color=data.user_color,
            skill_level=data.skill_level,
            history_complete=False,
            legacy_undo_fen=undo,
            base_last_move=data.last_move,
        )
        state.refresh_result()
        return state

    def refresh_result(self):
        outcome = self.board().outcome(claim_draw=False)
        self.status = 'finished' if outcome else 'playing'
        self.result = outcome.result() if outcome else '*'

    def undo(self):
        if self.turn_starts:
            boundary = self.turn_starts.pop()
            self.moves_uci = self.moves_uci[:boundary]
        elif self.legacy_undo_fen:
            self.initial_fen = self.legacy_undo_fen
            self.legacy_undo_fen = None
            self.base_last_move = ''
            self.moves_uci = []
        else:
            raise ValueError('UNDO_UNAVAILABLE')
        self.refresh_result()

    def legacy_snapshot(self):
        board = self.board()
        previous = self.legacy_undo_fen or ''
        if self.turn_starts:
            previous_board = chess.Board(self.initial_fen)
            for uci in self.moves_uci[: self.turn_starts[-1]]:
                previous_board.push_uci(uci)
            previous = previous_board.fen()
        return {
            '_version': 2,
            'board_state': board.fen(),
            'prev_board_state': previous,
            'skill_state': 'GAME_OVER' if self.status == 'finished' else 'WAITING_MOVE',
            'prev_skill_state': 'WAITING_MOVE',
            'user_color': self.user_color,
            'skill_level': self.skill_level,
            'time_level': 0.1,
            'last_move': self.last_move(),
            'move_count': len(self.turn_starts),
        }

    def last_move(self):
        board = self.board()
        if not board.move_stack:
            return self.base_last_move
        last = board.pop()
        return board.san(last)
