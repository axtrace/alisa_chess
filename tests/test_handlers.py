import unittest
from unittest.mock import Mock, patch

import chess
from chess import Board

import texts
from game import Game
from handlers.game_over_handler import GameOverHandler
from handlers.initiated_handler import InitiatedHandler
from handlers.waiting_color_handler import WaitingColorHandler
from handlers.waiting_confirm_handler import WaitingConfirmHandler
from handlers.waiting_draw_confirm_handler import WaitingDrawConfirmHandler
from handlers.waiting_move_handler import WaitingMoveHandler
from handlers.waiting_resign_confirm_handler import WaitingResignConfirmHandler


class TestHandlers(unittest.TestCase):
    """Тесты для обработчиков состояний."""

    def setUp(self):
        """Подготовка окружения для тестов."""
        self.game = Game()

    def test_initiated_handler(self):
        """Тест обработчика начального состояния."""
        request = {'request': {'command': 'начать игру', 'nlu': {'intents': {}}}}
        handler = InitiatedHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'WAITING_CONFIRM')

    def test_waiting_confirm_handler_yes(self):
        """Тест обработчика ожидания подтверждения с положительным ответом."""
        request = {'request': {'command': 'да', 'nlu': {'intents': {'YANDEX.CONFIRM': {}}}}}
        handler = WaitingConfirmHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'WAITING_COLOR')

    def test_waiting_color_handler_white(self):
        """Тест обработчика выбора цвета с выбором белых."""
        request = {'request': {'command': 'белые', 'nlu': {'intents': {}}}}
        handler = WaitingColorHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertIn('е четыре', response['tts'])
        self.assertIn('конь эф три', response['tts'])
        self.assertEqual(self.game.get_skill_state(), 'WAITING_MOVE')

    def test_waiting_move_handler_help(self):
        """Тест обработчика ожидания хода с запросом помощи."""
        self.game.set_skill_state('WAITING_MOVE')
        request = {'request': {'command': 'помощь', 'nlu': {'intents': {'YANDEX.HELP': {}}}}}
        handler = WaitingMoveHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)

    def test_waiting_draw_confirm_handler_yes(self):
        """Тест обработчика подтверждения ничьей с положительным ответом."""
        self.game.set_skill_state('WAITING_DRAW_CONFIRM')
        request = {'request': {'command': 'да', 'nlu': {'intents': {'YANDEX.CONFIRM': {}}}}}
        handler = WaitingDrawConfirmHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')

    def test_waiting_resign_confirm_handler_yes(self):
        """Тест обработчика подтверждения сдачи с положительным ответом."""
        self.game.set_skill_state('WAITING_RESIGN_CONFIRM')
        request = {'request': {'command': 'да', 'nlu': {'intents': {'YANDEX.CONFIRM': {}}}}}
        handler = WaitingResignConfirmHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')

    def test_game_over_handler_new_game(self):
        """Тест обработчика окончания игры с запросом новой игры."""
        self.game.set_skill_state('GAME_OVER')
        request = {'request': {'command': 'новая игра', 'nlu': {'intents': {'NEW_GAME': {}}}}}
        handler = GameOverHandler(self.game, request)
        response = handler.handle()

        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')


class TestCheckGameStateDraws(unittest.TestCase):
    """Тесты на ничью по троекратному повторению и правилу 50 ходов (T-02)."""

    def setUp(self):
        self.game = Game()
        self.game.set_skill_state('WAITING_MOVE')
        self.game.user_color = 'WHITE'
        request = {'request': {'command': '', 'nlu': {'intents': {}}}}
        self.handler = WaitingMoveHandler(self.game, request)

    def _make_move(self, uci):
        self.game.board.push(chess.Move.from_uci(uci))

    def test_threefold_repetition_claim(self):
        """При троекратном повторении позиции объявляется ничья."""
        # Повторяем позицию: Nf3/Nf6/Ng1/Ng8 дважды → начальная позиция встречается 3 раза
        for _ in range(2):
            self._make_move('g1f3')
            self._make_move('g8f6')
            self._make_move('f3g1')
            self._make_move('f6g8')

        self.assertTrue(self.game.can_claim_threefold_repetition())
        self.assertFalse(self.game.is_fivefold_repetition())

        response = self.handler._check_game_state(current_move='Ng8', prev_turn='BLACK')

        self.assertIsNotNone(response)
        self.assertIn('троекратного повторения', response['text'])
        self.assertEqual(self.game.get_skill_state(), 'GAME_OVER')

    def test_fifty_moves_rule_claim(self):
        """При достижении 50 ходов без взятий и ходов пешкой объявляется ничья."""
        # halfmove_clock = 100 → можно требовать ничью по правилу 50 ходов.
        # Берём позицию с достаточным материалом (K+R vs K), чтобы не сработал
        # is_insufficient_material раньше правила 50 ходов.
        self.game.board = chess.Board('4k3/8/8/8/8/8/8/R3K3 w - - 100 60')

        self.assertTrue(self.game.can_claim_fifty_moves())
        self.assertFalse(self.game.is_insufficient_material())

        response = self.handler._check_game_state(current_move='Ke3', prev_turn='BLACK')

        self.assertIsNotNone(response)
        self.assertIn('50 ходов', response['text'])
        self.assertEqual(self.game.get_skill_state(), 'GAME_OVER')

    def test_no_draw_in_normal_position(self):
        """В обычной позиции _check_game_state не объявляет ничью."""
        self._make_move('e2e4')
        response = self.handler._check_game_state(current_move='e4', prev_turn='WHITE')
        self.assertIsNone(response)
        self.assertEqual(self.game.get_skill_state(), 'WAITING_MOVE')


class TestUserMoveIntegrity(unittest.TestCase):
    """Регресс-тесты T-03: «Алиса жульничает» / забирает уведённую из-под боя фигуру.

    Проверяемые инварианты:
      1. При AMBIGUOUS доска НЕ модифицируется (нет молчаливого выбора первого хода).
      2. При успешном ходе фактический FEN доски строго соответствует возвращённому SAN.
      3. После ухода фигуры из-под боя ход пользователя действительно применяется
         к доске: «съеденной» фигуры уже нет на исходной клетке, и компьютер
         оперирует обновлённой позицией.
    """

    def setUp(self):
        self.game = Game()
        self.game.set_skill_state('WAITING_MOVE')
        self.game.user_color = 'WHITE'

    def _make_handler(self, command, intents=None):
        request = {
            'request': {
                'command': command,
                'nlu': {'intents': intents or {}, 'tokens': command.lower().split()},
            }
        }
        return WaitingMoveHandler(self.game, request)

    def test_ambiguous_move_does_not_modify_board(self):
        """T-03: при AMBIGUOUS доска должна остаться нетронутой."""
        # Оба коня (b1 и g1 в стартовой позиции — нет; ставим вручную)
        # Позиция: два коня могут пойти на e4 → ход «конь на e4» неоднозначен.
        # 8/8/8/8/8/2N1N3/8/8 w - - 0 1 — кони c3 и e3 (c3 ходит Ne4, e3 ходит Ne4? нет).
        # Проще: кони на c3 и g3, оба могут пойти на e4.
        self.game.board = chess.Board('4k3/8/8/8/8/2N3N1/8/4K3 w - - 0 1')

        legal_to_e4 = [m for m in self.game.board.legal_moves if self.game.board.san(m).endswith('e4')]
        # Должно быть как минимум два кандидата — Nce4 и Nge4
        self.assertGreaterEqual(len(legal_to_e4), 2)

        fen_before = self.game.board.fen()

        handler = self._make_handler(
            'конь на e4',
            intents={
                'CHESS_MOVE': {
                    'slots': {
                        'piece': {'value': 'конь'},
                        'file_to': {'value': 'e'},
                        'rank_to': {'value': '4'},
                    }
                }
            },
        )
        user_moves, reason_type = handler._handle_user_move()

        self.assertEqual(reason_type, 'AMBIGUOUS')
        self.assertIsInstance(user_moves, list)
        self.assertGreaterEqual(len(user_moves), 2)
        # Главный инвариант: доска не изменилась.
        self.assertEqual(self.game.board.fen(), fen_before)

    def test_successful_move_board_matches_returned_san(self):
        """T-03: после OK-хода FEN доски совпадает с FEN, который даёт push_san(returned_san)."""
        # Берём стартовую позицию, ход e2-e4 однозначен.
        handler = self._make_handler(
            'e2 e4',
            intents={
                'CHESS_MOVE': {
                    'slots': {
                        'file_from': {'value': 'e'},
                        'rank_from': {'value': '2'},
                        'file_to': {'value': 'e'},
                        'rank_to': {'value': '4'},
                    }
                }
            },
        )

        # Эталон: применяем тот же SAN к чистой доске.
        reference_board = chess.Board()
        user_move, reason_type = handler._handle_user_move()
        self.assertEqual(reason_type, 'OK')
        self.assertIsInstance(user_move, str)
        reference_board.push_san(user_move)

        self.assertEqual(self.game.board.fen(), reference_board.fen())

    def test_piece_moved_out_of_attack_engine_sees_updated_board(self):
        """T-03: пользователь уводит фигуру из-под боя — на исходной клетке её больше нет.

        Сценарий: чёрная ладья на e5 под боем белой ладьи e1. Ход пользователя (за чёрных)
        Re5-a5 уводит ладью из-под боя. После применения хода:
          * на e5 — пусто;
          * белая ладья e1 не может «съесть» ничего на e5, потому что там пусто.
        """
        # Сначала за чёрных делает ход пользователь.
        # Чёрный король на a8 (вне линии e), чтобы уход ладьи с e5 был легален.
        self.game.user_color = 'BLACK'
        self.game.board = chess.Board('k7/8/8/4r3/8/8/8/4R2K b - - 0 1')

        handler = self._make_handler(
            'ладья e5 a5',
            intents={
                'CHESS_MOVE': {
                    'slots': {
                        'piece': {'value': 'ладья'},
                        'file_from': {'value': 'e'},
                        'rank_from': {'value': '5'},
                        'file_to': {'value': 'a'},
                        'rank_to': {'value': '5'},
                    }
                }
            },
        )

        user_move, reason_type = handler._handle_user_move()
        self.assertEqual(reason_type, 'OK')
        self.assertEqual(user_move, 'Ra5')

        # На e5 не должно остаться чёрной ладьи (фигура ушла).
        self.assertIsNone(self.game.board.piece_at(chess.E5))
        # На a5 теперь чёрная ладья.
        piece_a5 = self.game.board.piece_at(chess.A5)
        self.assertIsNotNone(piece_a5)
        self.assertEqual(piece_a5.symbol(), 'r')

        # Дополнительная проверка: легальные ходы для белой ладьи e1 не включают «взятие» e5.
        legal_sans = [self.game.board.san(m) for m in self.game.board.legal_moves]
        self.assertNotIn('Rxe5', legal_sans)
        self.assertNotIn('Rxe5+', legal_sans)
        self.assertNotIn('Rxe5#', legal_sans)

    def _assert_engine_failure_rolls_back_turn(self, *, engine_result=None, engine_error=None):
        """Проверяет атомарность пары «ход игрока → ход Stockfish»."""
        for san in ('Nf3', 'Nf6', 'Ng1', 'Ng8'):
            self.game.board.push_san(san)
        self.game.last_move = 'Ng8'

        board_before = self.game.board.copy(stack=True)
        self.game._engine = Mock()
        if engine_error is not None:
            self.game._engine.play.side_effect = engine_error
        else:
            self.game._engine.play.return_value = engine_result

        handler = self._make_handler(
            'e4',
            intents={
                'CHESS_MOVE': {
                    'slots': {
                        'file_to': {'value': 'e'},
                        'rank_to': {'value': '4'},
                    }
                }
            },
        )
        response = handler.safe_handle()

        self.assertIn('ошибка', response['text'].lower())
        self.assertFalse(response['end_session'])
        self.assertEqual(self.game.board.fen(), board_before.fen())
        self.assertEqual(self.game.board.move_stack, board_before.move_stack)
        self.assertEqual(self.game.get_last_move(), 'Ng8')
        self.assertEqual(self.game.who(), 'White')

    def test_engine_exception_rolls_back_user_move(self):
        """При исключении Stockfish ход игрока не сохраняется как незавершённый полуход."""
        self._assert_engine_failure_rolls_back_turn(engine_error=RuntimeError('engine unavailable'))

    def test_empty_engine_move_rolls_back_user_move(self):
        """Пустой bestmove не оставляет доску на ходе компьютера."""
        self._assert_engine_failure_rolls_back_turn(engine_result=Mock(move=None))


if __name__ == '__main__':
    unittest.main()
