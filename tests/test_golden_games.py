"""Интеграционные «золотые партии».

Эти тесты проверяют, что навык корректно обрабатывает реалистичные
последовательности запросов Алисы: состояние одного ответа передаётся
во вход следующего запроса (как это делает платформа), а реакции
проверяются на полном response payload, а не на отдельных моках.

Stockfish заменён глобальной фикстурой в `tests/conftest.py` стабом,
который всегда отвечает e2e4. Это накладывает ограничение на сценарии
с большим числом ходов компьютера, поэтому здесь мы покрываем
короткие, но информативные сценарии.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import chess

from alice_serverless import handler
from skill_state import SkillState


def _base_event():
    """Минимальный шаблон запроса Алисы."""
    return {
        'meta': {
            'locale': 'ru-RU',
            'timezone': 'UTC',
            'client_id': 'ru.yandex.searchplugin/7.16',
            'interfaces': {'screen': {}},
        },
        'session': {
            'message_id': 0,
            'session_id': 'golden-session',
            'skill_id': 'golden-skill',
            'user': {'user_id': 'golden-user'},
            'application': {'application_id': 'golden-app'},
            'user_id': 'golden-user',
            'new': True,
        },
        'request': {
            'command': '',
            'original_utterance': '',
            'nlu': {'tokens': [], 'entities': [], 'intents': {}},
            'markup': {'dangerous_context': False},
            'type': 'SimpleUtterance',
        },
        'state': {'session': {}, 'user': {}, 'application': {}},
        'version': '1.0',
    }


def make_event(command, intents=None, *, user_state=None, session_state=None, message_id=0, new=False):
    """Собирает запрос Алисы с заданными командой/интентами и накопленным состоянием."""
    event = _base_event()
    event['session']['new'] = new
    event['session']['message_id'] = message_id
    event['request']['command'] = command
    event['request']['original_utterance'] = command
    if command:
        event['request']['nlu']['tokens'] = command.split()
    if intents:
        event['request']['nlu']['intents'] = intents
    if user_state:
        event['state']['user'] = {'game_state': user_state}
    if session_state:
        event['state']['session'] = session_state
    return event


class GoldenSession:
    """Имитирует клиента Алисы: прокидывает state из ответа в следующий запрос."""

    def __init__(self):
        self.user_state = None
        self.session_state = None
        self.message_id = 0
        self.responses = []

    def send(self, command, intents=None, *, new=False):
        event = make_event(
            command,
            intents=intents,
            user_state=self.user_state,
            session_state=self.session_state,
            message_id=self.message_id,
            new=new,
        )
        self.last_event = event
        response = handler(event, None)
        self.responses.append(response)
        self.user_state = (response.get('user_state_update') or {}).get('game_state')
        self.session_state = response.get('session_state')
        self.message_id += 1
        return response

    def resend_last(self):
        """Повторяет последний запрос с тем же message_id (идемпотентность)."""
        last = self.responses[-1]
        event = dict(self.last_event)
        event['state'] = {'user': {'game_state': self.user_state}, 'session': self.session_state}
        response = handler(event, None)
        self.responses.append(response)
        self.user_state = response['user_state_update']['game_state']
        self.session_state = response['session_state']
        return response, last


class TestGoldenGames(unittest.TestCase):
    """Golden-сценарии: фиксированные последовательности → проверяем полный response."""

    def _assert_response_shape(self, response):
        """Каждый ответ должен иметь обязательные поля Алисы."""
        self.assertEqual(response['version'], '1.0')
        self.assertIn('session', response)
        self.assertIn('response', response)
        self.assertIn('text', response['response'])
        self.assertIn('tts', response['response'])
        self.assertIn('end_session', response['response'])
        self.assertIn('user_state_update', response)

    # ---------- Сценарий 1: старт с выбором белых ----------

    def test_start_white_flow(self):
        """Пустой первый запрос → «да» → «белые». Игрок ходит первым."""
        session = GoldenSession()

        # 1. Первый запрос без интентов — InitiatedHandler выдаёт приветствие
        #    и переводит в WAITING_CONFIRM.
        r1 = session.send('')
        self._assert_response_shape(r1)
        self.assertFalse(r1['response']['end_session'])
        self.assertEqual(session.user_state['skill_state'], SkillState.WAITING_CONFIRM.value)

        # 2. «Да» → переход к выбору цвета
        r2 = session.send('да')
        self._assert_response_shape(r2)
        self.assertEqual(session.user_state['skill_state'], SkillState.WAITING_COLOR.value)

        # 3. «Белые» → стартует партия, ход пользователя
        r3 = session.send('белые')
        self._assert_response_shape(r3)
        self.assertEqual(session.user_state['skill_state'], SkillState.WAITING_MOVE.value)
        self.assertEqual(session.user_state['user_color'], 'WHITE')
        # Доска не тронута — компьютер ещё не ходил
        self.assertTrue(session.user_state['board_state'].startswith('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'))
        self.assertIn('ход', r3['response']['text'].lower())

    # ---------- Сценарий 2: старт с выбором чёрных (компьютер ходит первым) ----------

    def test_start_black_flow(self):
        """Игрок выбирает чёрных → компьютер сразу делает ход e2e4."""
        session = GoldenSession()
        session.send('')
        session.send('да')
        # Используем интент BLACK_WORD: extract_color по тексту работает только
        # с формой без «ё» («черные»), а через интент — детерминированно.
        r3 = session.send('черные', intents={'BLACK_WORD': {}})

        self._assert_response_shape(r3)
        self.assertEqual(session.user_state['skill_state'], SkillState.WAITING_MOVE.value)
        self.assertEqual(session.user_state['user_color'], 'BLACK')
        # Компьютер сходил e2e4 — пешка на e4
        self.assertIn(
            'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR',
            session.user_state['board_state'],
        )

    # ---------- Сценарий 3: идемпотентность по message_id ----------

    def test_idempotency_same_message_id(self):
        """Повтор запроса с тем же message_id возвращает кэшированный response."""
        session = GoldenSession()
        for command in ('', 'да'):
            session.send(command)
            repeat, original = session.resend_last()
            self.assertEqual(repeat, original)

    def test_move_duplicate_undo_and_repeat(self):
        session = GoldenSession()
        for command in ('', 'да', 'белые'):
            session.send(command)
        before = session.user_state['board_state']
        engine = MagicMock()
        engine.play.return_value.move = chess.Move.from_uci('e7e5')
        with patch('chess.engine.SimpleEngine.popen_uci', return_value=engine):
            session.send('e4', {'CHESS_MOVE': {'slots': {'file_to': {'value': 'e'}, 'rank_to': {'value': '4'}}}})
            self.assertEqual(session.user_state['last_move'], 'e5')
            repeat, original = session.resend_last()
            self.assertEqual(repeat, original)
            session.send('отмени ход', {'UNDO': {}})
            self.assertEqual(session.user_state['board_state'], before)
            self.assertEqual(session.user_state['last_move'], '')
            reply = session.send('повтори ход', {'REPEAT_LAST_MOVE': {}})
            self.assertNotIn('e5', reply['response']['text'])
            engine.play.assert_called_once()

    # ---------- Сценарий 4: помощь во время партии не ломает состояние ----------

    def test_help_during_game_preserves_state(self):
        """В WAITING_MOVE «помощь» отвечает текстом помощи, не меняя ход."""
        session = GoldenSession()
        session.send('')
        session.send('да')
        session.send('белые')
        board_before = session.user_state['board_state']
        state_before = session.user_state['skill_state']

        r_help = session.send('помощь', intents={'YANDEX.HELP': {}})
        self._assert_response_shape(r_help)
        # Состояние не сдвинулось
        self.assertEqual(session.user_state['board_state'], board_before)
        self.assertEqual(session.user_state['skill_state'], state_before)

    # ---------- Сценарий 5: сдача через подтверждение ----------

    def test_resign_flow(self):
        """«Сдаюсь» → запрос подтверждения → «да» → GAME_OVER."""
        session = GoldenSession()
        session.send('')
        session.send('да')
        session.send('белые')

        r_resign = session.send('сдаюсь', intents={'RESIGN': {}})
        self._assert_response_shape(r_resign)
        self.assertEqual(
            session.user_state['skill_state'],
            SkillState.WAITING_RESIGN_CONFIRM.value,
        )

        r_confirm = session.send('да')
        self._assert_response_shape(r_confirm)
        # После подтверждения сдачи навык переходит обратно в INITIATED
        # (готов начать новую партию) — см. WaitingResignConfirmHandler.on_accept.
        self.assertEqual(session.user_state['skill_state'], SkillState.INITIATED.value)

    # ---------- Сценарий 6: новая игра в середине партии ----------

    def test_new_game_in_progress(self):
        """«Новая игра» в WAITING_MOVE → подтверждение → сброс к WAITING_COLOR."""
        session = GoldenSession()
        session.send('')
        session.send('да')
        session.send('белые')

        r_new = session.send('новая игра', intents={'NEW_GAME': {}})
        self._assert_response_shape(r_new)
        self.assertEqual(
            session.user_state['skill_state'],
            SkillState.WAITING_NEWGAME_CONFIRM.value,
        )

        r_confirm = session.send('да')
        self._assert_response_shape(r_confirm)
        # После подтверждения навык снова ждёт выбора цвета
        self.assertEqual(session.user_state['skill_state'], SkillState.WAITING_COLOR.value)
        # Доска сброшена
        self.assertTrue(session.user_state['board_state'].startswith('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'))


def test_spoken_position_repeats_and_fits_session_state(_stub_stockfish_engine):
    session = GoldenSession()
    for command in ('', 'да', 'белые'):
        session.send(command)
    before = session.user_state
    response = session.send('назови позицию', new=True)['response']
    assert 'кони b1, g1' in response['text']
    assert 'кони бэ 8, же 8' in response['tts']
    assert len(json.dumps(session.session_state, ensure_ascii=False).encode()) <= 1024
    assert session.send('повтори', {'YANDEX.REPEAT': {}})['response'] == response
    assert session.send('где мои кони?')['response']['text'] == 'Ваши кони на b1, g1.'
    assert session.user_state == before
    _stub_stockfish_engine.assert_not_called()


def test_knights_follow_player_color_and_captures(_stub_stockfish_engine):
    from game import Game

    game = Game()
    game.set_skill_state(SkillState.WAITING_MOVE)
    game.set_user_color('BLACK')
    game.board = chess.Board('3nk3/8/8/8/8/8/8/1N2K3 b - - 0 1')
    session = GoldenSession()
    session.user_state = game.serialize_state()
    assert session.send('где мой конь')['response']['tts'] == 'Ваш конь на дэ 8.'
    game.board.remove_piece_at(chess.D8)
    session.user_state = game.serialize_state()
    assert session.send('где мои кони')['response']['text'] == 'У вас не осталось коней.'
    _stub_stockfish_engine.assert_not_called()


def test_undo_restores_prior_engine_move_after_restart():
    from game import Game

    board = chess.Board()
    for move in ('e4', 'e5'):
        board.push_san(move)
    session = GoldenSession()
    game = Game()
    game.board = board
    game.set_user_color('WHITE')
    game.set_skill_state(SkillState.WAITING_MOVE)
    game.last_move = 'e5'
    session.user_state = game.serialize_state()
    session.user_state.pop('prev_last_move')  # Existing V2 game.
    engine = MagicMock()
    engine.play.return_value.move = chess.Move.from_uci('b8c6')
    with patch('chess.engine.SimpleEngine.popen_uci', return_value=engine):
        session.send(
            'конь f3',
            {
                'CHESS_MOVE': {
                    'slots': {
                        'piece': {'value': 'конь'},
                        'file_to': {'value': 'f'},
                        'rank_to': {'value': '3'},
                    }
                }
            },
        )
    assert session.user_state['last_move'] == 'Nc6'
    session.send('отмена', {'UNDO': {}})
    assert session.user_state['board_state'] == board.fen()
    assert session.user_state['last_move'] == 'e5'
    assert not session.user_state['prev_board_state']


if __name__ == '__main__':
    unittest.main()
