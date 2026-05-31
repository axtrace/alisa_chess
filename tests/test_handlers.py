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


if __name__ == '__main__':
    unittest.main()
