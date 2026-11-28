"""Штатный голосовой диалог, выполняемый вне транзакции общей партии."""

from copy import deepcopy
from functools import partial

import chess

from alice_chess import AliceChess
from game import Game
from move_extractor import MoveExtractor
from shared_chess.moves import extract_move
from shared_chess.state import SharedGameState
from skill_state import SkillState


class VoiceGame(Game):
    """Сохраняет поведение Game и использует движок общего сервиса."""

    def __init__(self, *, engine, history=None, game_state=None):
        super().__init__(game_state=game_state)
        self.move_engine = engine
        self.history = history
        self.engine_failed = False

    def _history_board(self):
        # Рендер использует стек текущей реплики, правила и движок — всю историю.
        if self.history is None or self.board.root().fen() != self.history.fen():
            return self.board.copy(stack=True)
        board = self.history.copy(stack=True)
        for move in self.board.move_stack:
            board.push(move)
        return board

    def is_fivefold_repetition(self):
        return self._history_board().is_fivefold_repetition()

    def can_claim_threefold_repetition(self):
        return self._history_board().can_claim_threefold_repetition()

    def comp_move(self):
        try:
            move = self.move_engine(self._history_board(), self.skill_level)
            san = self.board.san(move)
            if move not in self.board.legal_moves:
                raise ValueError('Illegal engine move')
            self.board.push(move)
            self.last_move = san
            return san
        except Exception:
            self.engine_failed = True
            raise


def play_dialog(state, snapshot, payload, engine):
    if payload.get('legacy_confirmation'):
        stage = {'new_game': SkillState.WAITING_NEWGAME_CONFIRM, 'resign': SkillState.WAITING_RESIGN_CONFIRM}
        snapshot = {
            **snapshot,
            'skill_state': stage[payload['legacy_confirmation']],
            'prev_skill_state': SkillState.WAITING_MOVE,
        }
    event = {
        'session': payload['session'],
        'request': payload['request'],
        # Внутренний вызов не содержит аккаунта; снимок уже выбран по owner.
        'state': {'application': {'game_state': snapshot}, 'session': {}},
    }
    # Сохраняем поддержку произнесённых координат без NLU в прежнем пилоте.
    if snapshot.get('skill_state') == SkillState.WAITING_MOVE and not payload['request'].get('nlu', {}).get('intents'):
        board = chess.Board(snapshot['board_state'])
        if MoveExtractor().extract_move(event, board)[1] is None:
            try:
                move = extract_move(board, payload['request'].get('command', ''))
            except ValueError:
                pass
            else:
                source, target = chess.square_name(move.from_square), chess.square_name(move.to_square)
                values = {
                    'piece': chess.piece_name(board.piece_type_at(move.from_square)),
                    'file_from': source[0],
                    'rank_from': source[1],
                    'file_to': target[0],
                    'rank_to': target[1],
                    'promotion_piece': chess.piece_name(move.promotion) if move.promotion else '',
                }
                event['request'] = deepcopy(payload['request'])
                event['request'].setdefault('nlu', {})['intents'] = {
                    'CHESS_MOVE': {'slots': {key: {'value': value} for key, value in values.items()}},
                }
    factory = partial(VoiceGame, engine=engine, history=state.board() if state else None)
    with AliceChess(game_factory=factory) as alice:
        response = alice.handle_request(event)
        if alice.game.engine_failed:
            # Выбор чёрных тоже вызывает движок. Ошибка откатывает весь переход.
            return state, snapshot, response
        game = alice.game
        updated = alice.get_game_state()
        if not game.user_color:
            return None, updated, response

        created = state is None
        if created:
            root = game.board.root().fen()
            state = SharedGameState(
                initial_fen=root,
                user_color=game.user_color,
                skill_level=game.skill_level,
                history_complete=root == chess.STARTING_FEN,
            )
        before = state.board().fen()
        if game.board.move_stack:
            if game.board.root().fen() != before:
                raise ValueError('Voice move does not continue the shared position')
            if game.prev_board == before:
                state.turn_starts.append(len(state.moves_uci))
            state.moves_uci.extend(move.uci() for move in game.board.move_stack)
        elif game.board.fen() != before:
            state.undo()
            if state.board().fen() != game.board.fen():
                raise ValueError('Voice undo does not match the shared history')
            if not state.moves_uci:
                state.base_last_move = game.last_move

        state.user_color, state.skill_level = game.user_color, game.skill_level
        if created or state.board().fen() != before or snapshot.get('skill_state') == SkillState.WAITING_COLOR:
            state.refresh_result()
        previous_stage = snapshot.get('skill_state')
        if game.skill_state == SkillState.INITIATED:
            if previous_stage == SkillState.WAITING_RESIGN_CONFIRM:
                state.status = 'finished'
                state.result = '0-1' if game.user_color == 'WHITE' else '1-0'
            elif previous_stage == SkillState.WAITING_DRAW_CONFIRM:
                state.status, state.result = 'finished', '1/2-1/2'
        elif game.skill_state == SkillState.GAME_OVER:
            outcome = state.board().outcome(claim_draw=True)
            state.status, state.result = 'finished', outcome.result() if outcome else '*'
        return state, updated, response
