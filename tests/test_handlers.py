import unittest
from unittest.mock import Mock, patch
from game import Game
from chess import Board
from handlers.initiated_handler import InitiatedHandler
from handlers.waiting_confirm_handler import WaitingConfirmHandler
from handlers.waiting_color_handler import WaitingColorHandler
from handlers.waiting_move_handler import WaitingMoveHandler
from handlers.waiting_promotion_handler import WaitingPromotionHandler
from handlers.waiting_draw_confirm_handler import WaitingDrawConfirmHandler
from handlers.waiting_resign_confirm_handler import WaitingResignConfirmHandler
from handlers.game_over_handler import GameOverHandler


class TestHandlers(unittest.TestCase):
    """Тесты для обработчиков состояний."""
    
    def setUp(self):
        """Подготовка окружения для тестов."""
        self.game = Game()
        
    def test_initiated_handler(self):
        """Тест обработчика начального состояния."""
        request = {
            'request': {
                'command': 'начать игру',
                'nlu': {
                    'intents': {}
                }
            }
        }
        handler = InitiatedHandler(self.game, request)
        response = handler.handle()
        
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'WAITING_CONFIRM')
        
    def test_waiting_confirm_handler_yes(self):
        """Тест обработчика ожидания подтверждения с положительным ответом."""
        request = {
            'request': {
                'command': 'да',
                'nlu': {
                    'intents': {
                        'YANDEX.CONFIRM': {}
                    }
                }
            }
        }
        handler = WaitingConfirmHandler(self.game, request)
        response = handler.handle()
        
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'WAITING_COLOR')
        
    def test_waiting_color_handler_white(self):
        """Тест обработчика выбора цвета с выбором белых."""
        request = {
            'request': {
                'command': 'белые',
                'nlu': {
                    'intents': {}
                }
            }
        }
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
        request = {
            'request': {
                'command': 'помощь',
                'nlu': {
                    'intents': {
                        'YANDEX.HELP': {}
                    }
                }
            }
        }
        handler = WaitingMoveHandler(self.game, request)
        response = handler.handle()
        
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        
    def test_waiting_promotion_handler(self):
        """Тест обработчика превращения пешки."""
        self.game.set_skill_state('WAITING_PROMOTION')
        request = {
            'request': {
                'command': 'ферзь',
                'nlu': {
                    'intents': {}
                }
            }
        }
        handler = WaitingPromotionHandler(self.game, request)
        response = handler.handle()
        
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        
    def test_waiting_draw_confirm_handler_yes(self):
        """Тест обработчика подтверждения ничьей с положительным ответом."""
        self.game.set_skill_state('WAITING_DRAW_CONFIRM')
        request = {
            'request': {
                'command': 'да',
                'nlu': {
                    'intents': {
                        'YANDEX.CONFIRM': {}
                    }
                }
            }
        }
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
        request = {
            'request': {
                'command': 'да',
                'nlu': {
                    'intents': {
                        'YANDEX.CONFIRM': {}
                    }
                }
            }
        }
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
        request = {
            'request': {
                'command': 'новая игра',
                'nlu': {
                    'intents': {
                        'NEW_GAME': {}
                    }
                }
            }
        }
        handler = GameOverHandler(self.game, request)
        response = handler.handle()
        
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')


if __name__ == '__main__':
    unittest.main()