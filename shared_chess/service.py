"""Команды общей партии: резервирование → расчёт вне транзакции → commit."""

import hashlib
import time
import uuid
from typing import Any, Literal

import chess
from pydantic import BaseModel, ConfigDict, Field

from game import Game
from shared_chess.moves import extract_move
from shared_chess.repository import encode
from shared_chess.state import SharedGameState


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: uuid.UUID
    game_id: str | None
    expected_revision: int | None = Field(ge=0)
    type: Literal['move', 'move_text', 'new_game', 'undo', 'resign', 'set_level']
    payload: dict[str, Any] = Field(default_factory=dict)


class ServiceError(Exception):
    def __init__(self, code, message, status=409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


MESSAGES = {
    'OK': 'Готово.',
    'INVALID_MOVE': 'Такой ход сейчас недоступен.',
    'MOVE_NOT_UNDERSTOOD': 'Не удалось понять ход. Назовите исходную и конечную клетки.',
    'AMBIGUOUS_MOVE': 'Подходят несколько ходов. Уточните исходную клетку.',
    'UNDO_UNAVAILABLE': 'Предыдущего хода для отмены нет.',
    'GAME_FINISHED': 'Партия закончена. Можно начать новую.',
    'NOT_YOUR_TURN': 'Сейчас ход компьютера.',
    'ENGINE_ERROR': 'Движок временно недоступен. Позиция сохранена.',
    'INVALID_SETTINGS': 'Проверьте цвет и уровень сложности от 1 до 20.',
}


def stockfish_move(board, level):
    with Game(skill_level=level) as game:
        game.board = board.copy(stack=True)
        game.set_skill_level(level)
        game.time_level = min(game.time_level, 1.0)
        move_san = game.comp_move()
        if not move_san:
            raise RuntimeError('Stockfish did not return a move')
        return board.parse_san(move_san)


class GameService:
    def __init__(self, repository, engine=stockfish_move, clock=time.time):
        self.repository, self.engine, self.clock = repository, engine, clock

    def _snapshot(self, tx, owner):
        player = tx.get('players', owner)
        if not player or not player.get('game_id'):
            return {
                'game_id': None,
                'revision': None,
                'active_generation': 0,
                'busy': bool(player and player.get('operation')),
            }
        record = tx.get('games', owner, player['game_id'])
        if not record:
            raise ServiceError('RESTORE_FAILED', 'Общая партия не найдена. Требуется восстановление.', 503)
        state = SharedGameState.model_validate(record['state'])
        board = state.board()
        history_board = chess.Board(state.initial_fen)
        history = []
        for uci in state.moves_uci:
            move = chess.Move.from_uci(uci)
            history.append(history_board.san(move))
            history_board.push(move)
        user_turn = board.turn == (state.user_color == 'WHITE') and state.status == 'playing'
        return {
            'game_id': player['game_id'],
            'revision': record['revision'],
            'active_generation': player['generation'],
            'fen': board.fen(),
            'pieces': {chess.square_name(s): p.symbol() for s, p in board.piece_map().items()},
            'legal_moves': [m.uci() for m in board.legal_moves] if user_turn else [],
            'history_san': history,
            'history_complete': state.history_complete,
            'last_move': state.last_move(),
            'user_color': state.user_color,
            'skill_level': state.skill_level,
            'status': state.status,
            'result': state.result,
            'check': board.is_check(),
            'can_undo': bool(state.turn_starts or state.legacy_undo_fen),
            'busy': bool(player.get('operation')),
        }

    def current(self, owner):
        return self.repository.atomic(lambda tx: self._snapshot(tx, owner))

    def result(self, owner, operation_id):
        record = self.repository.atomic(lambda tx: tx.get('commands', owner, operation_id))
        return (
            record.get('result')
            if record and record['status'] == 'DONE'
            else {'status': 'RUNNING' if record else 'NOT_FOUND', 'code': 'IN_PROGRESS' if record else 'NOT_FOUND'}
        )

    def execute(self, owner, operation_id, command, reply_context=None):
        command = Command.model_validate(command).model_dump(mode='json')
        digest = hashlib.sha256(encode(command).encode()).hexdigest()
        # Generated outside retriable callbacks, so retries keep the same identity.
        new_game_id = str(uuid.uuid4())

        def reserve(tx):
            now = self.clock()
            saved = tx.get('commands', owner, operation_id)
            if saved and saved['digest'] != digest:
                raise ServiceError('IDEMPOTENCY_KEY_REUSED', 'Этот номер запроса уже использован для другой команды.')
            if saved and saved['status'] == 'DONE':
                return {'result': saved['result']}
            player = tx.get('players', owner) or {'game_id': None, 'generation': 0}
            locked = player.get('operation')
            if locked and player['lease_until'] > now:
                return {
                    'result': {
                        'status': 'RUNNING',
                        'code': 'IN_PROGRESS' if locked == operation_id else 'GAME_BUSY',
                        'message': 'Предыдущий ход ещё обрабатывается.',
                    }
                }
            if locked and locked != operation_id:
                abandoned = tx.get('commands', owner, locked)
                return {'recover': abandoned}
            if command['game_id'] != player['game_id']:
                raise ServiceError('STALE_GAME', 'Партия изменилась. Обновите доску.')
            game = tx.get('games', owner, player['game_id']) if player['game_id'] else None
            if command['expected_revision'] != (game['revision'] if game else None):
                raise ServiceError('STALE_REVISION', 'Позиция изменилась. Повторите ход на обновлённой доске.')
            if not game and command['type'] != 'new_game':
                raise ServiceError('NO_GAME', 'Сначала начните новую партию.')
            attempt = (saved or {}).get('attempt', 0) + 1
            lease = now + 10
            entry = {
                'operation_id': operation_id,
                'command': command,
                'digest': digest,
                'status': 'RUNNING',
                'attempt': attempt,
                'lease_until': lease,
                'new_game_id': (saved or {}).get('new_game_id', new_game_id),
                'reply_context': (saved or {}).get('reply_context', reply_context),
            }
            player.update(operation=operation_id, lease_until=lease, attempt=attempt)
            tx.put('players', owner, '', player)
            tx.put('commands', owner, operation_id, entry)
            return {'entry': entry, 'game': game}

        reserved = self.repository.atomic(reserve)
        if 'recover' in reserved:
            abandoned = reserved['recover']
            if not abandoned:
                raise ServiceError('RESTORE_FAILED', 'Не найдена запись незавершённой команды.', 503)
            self.execute(owner, abandoned['operation_id'], abandoned['command'], abandoned.get('reply_context'))
            return {
                'status': 'RUNNING',
                'code': 'GAME_BUSY',
                'message': 'Предыдущая команда восстановлена. Повторите запрос.',
            }
        if 'result' in reserved:
            return reserved['result']
        entry, record = reserved['entry'], reserved['game']
        state = SharedGameState.model_validate(record['state']) if record else None
        before_state = state.model_copy(deep=True) if state else None
        code = 'OK'
        try:
            state = self._apply(state, command)
        except ValueError as error:
            code = str(error).split(':', 1)[0]
            if code not in MESSAGES:
                code = 'INVALID_MOVE'
            state = before_state
        except Exception:
            code, state = 'ENGINE_ERROR', before_state

        def commit(tx):
            now = self.clock()
            live = tx.get('commands', owner, operation_id)
            player = tx.get('players', owner)
            if live and live['status'] == 'DONE':
                return live['result']
            if (
                not live
                or not player
                or live['attempt'] != entry['attempt']
                or player.get('operation') != operation_id
                or player['lease_until'] <= now
            ):
                return {
                    'status': 'RUNNING',
                    'code': 'IN_PROGRESS',
                    'message': 'Результат уточняется. Повторите тот же запрос.',
                }
            current = tx.get('games', owner, player['game_id']) if player['game_id'] else None
            if (
                player['game_id'] != command['game_id']
                or (current['revision'] if current else None) != command['expected_revision']
            ):
                raise ServiceError('STALE_REVISION', 'Позиция изменилась во время расчёта.')
            if code == 'OK':
                if command['type'] == 'new_game':
                    player['game_id'] = entry['new_game_id']
                    player['generation'] += 1
                    revision = 1
                else:
                    revision = current['revision'] + 1
                tx.put('games', owner, player['game_id'], {'state': state.model_dump(), 'revision': revision})
            player.pop('operation', None)
            player.pop('lease_until', None)
            tx.put('players', owner, '', player)
            result = {
                'status': 'DONE',
                'code': code,
                'message': MESSAGES[code],
                'request_id': command['request_id'],
                'snapshot': self._snapshot(tx, owner),
            }
            context = entry.get('reply_context')
            if context:
                from shared_chess.replies import save_reply_in_transaction

                result['alice_reply'] = save_reply_in_transaction(tx, owner, context, result, state)
            live.update(status='DONE', result=result)
            tx.put('commands', owner, operation_id, live)
            return result

        return self.repository.atomic(commit)

    def _apply(self, state, command):
        kind, payload = command['type'], command['payload']
        if kind == 'new_game':
            if payload.get('user_color', 'WHITE') not in ('WHITE', 'BLACK'):
                raise ValueError('INVALID_SETTINGS')
            level = payload.get('skill_level', 1)
            if type(level) is not int or not 1 <= level <= 20:
                raise ValueError('INVALID_SETTINGS')
            state = SharedGameState(user_color=payload.get('user_color', 'WHITE'), skill_level=level)
            if state.user_color == 'BLACK':
                board = state.board()
                move = self.engine(board, level)
                if move not in board.legal_moves:
                    raise RuntimeError('Illegal engine move')
                state.moves_uci.append(move.uci())
            return state
        if kind == 'undo':
            state.undo()
            return state
        if kind == 'set_level':
            level = payload.get('skill_level')
            if type(level) is not int or not 1 <= level <= 20:
                raise ValueError('INVALID_SETTINGS')
            state.skill_level = level
            return state
        if state.status == 'finished':
            raise ValueError('GAME_FINISHED')
        if kind == 'resign':
            state.status, state.result = 'finished', '0-1' if state.user_color == 'WHITE' else '1-0'
            return state
        board = state.board()
        if board.turn != (state.user_color == 'WHITE'):
            raise ValueError('NOT_YOUR_TURN')
        if kind == 'move_text':
            move = extract_move(board, str(payload.get('text', ''))[:300])
        else:
            move = board.parse_uci(str(payload.get('uci', '')))
        if move not in board.legal_moves:
            raise ValueError('INVALID_MOVE')
        state.turn_starts.append(len(state.moves_uci))
        board.push(move)
        state.moves_uci.append(move.uci())
        if not board.is_game_over():
            reply = self.engine(board, state.skill_level)
            if reply not in board.legal_moves:
                raise RuntimeError('Illegal engine move')
            state.moves_uci.append(reply.uci())
        state.refresh_result()
        return state

    def import_legacy(self, owner, snapshot):
        state = SharedGameState.import_legacy(snapshot)
        game_id = str(uuid.uuid4())

        def migrate(tx):
            player = tx.get('players', owner)
            if player:
                return self._snapshot(tx, owner)
            tx.put('games', owner, game_id, {'state': state.model_dump(), 'revision': 1})
            tx.put('players', owner, '', {'game_id': game_id, 'generation': 1, 'storage_mode': 'shared'})
            return self._snapshot(tx, owner)

        return self.repository.atomic(migrate)
