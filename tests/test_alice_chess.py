import unittest
from unittest.mock import Mock, patch
from game import Game
from chess import Board
from alice_chess import AliceChess


class TestAliceChess(unittest.TestCase):
    """Тесты для класса AliceChess."""
    
    def setUp(self):
        """Подготовка окружения для тестов."""
        self.game = Game(board=Board())
        self.alice = AliceChess(self.game)
        
    def test_init(self):
        """Тест инициализации класса."""
        # Проверяем, что все необходимые атрибуты созданы
        self.assertIsNotNone(self.alice.game)
        self.assertIsNotNone(self.alice.speaker)
        self.assertIsNotNone(self.alice.text_preparer)
        
    def test_handle_request_initiated_state(self):
        """Тест обработки запроса в начальном состоянии."""
        # Подготавливаем тестовый запрос
        request = {
            'request': {
                'command': 'начать игру',
                'nlu': {
                    'intents': {}
                }
            }
        }
        
        # Вызываем обработчик
        response = self.alice.handle_request(request)
        
        # Проверяем результат
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        
    def test_handle_request_waiting_move(self):
        """Тест обработки запроса в состоянии ожидания хода."""
        # Устанавливаем состояние ожидания хода
        self.game.set_skill_state('WAITING_MOVE')
        
        # Подготавливаем тестовый запрос с ходом
        request = {
            'request': {
                'command': 'e2 e4',
                'nlu': {
                    'intents': {}
                }
            }
        }
        
        # Вызываем обработчик
        response = self.alice.handle_request(request)
        
        # Проверяем результат
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        
    def test_handle_request_invalid_state(self):
        """Тест обработки запроса с недопустимым состоянием."""
        # Устанавливаем недопустимое состояние
        self.game.set_skill_state('INVALID_STATE')
        
        # Подготавливаем тестовый запрос
        request = {
            'request': {
                'command': 'тест',
                'nlu': {
                    'intents': {}
                }
            }
        }
        
        # Проверяем, что вызов обработчика вызывает исключение
        with self.assertRaises(ValueError):
            self.alice.handle_request(request)
            
    def test_handle_request_help_intent(self):
        """Тест обработки запроса с намерением помощи."""
        # Устанавливаем состояние ожидания хода
        self.game.set_skill_state('WAITING_MOVE')
        
        # Подготавливаем тестовый запрос с намерением помощи
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
        
        # Вызываем обработчик
        response = self.alice.handle_request(request)
        
        # Проверяем результат
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        
    def test_handle_request_new_game_intent(self):
        """Тест обработки запроса с намерением новой игры."""
        # Устанавливаем состояние ожидания хода
        self.game.set_skill_state('WAITING_MOVE')
        
        # Подготавливаем тестовый запрос с намерением новой игры
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
        
        # Вызываем обработчик
        response = self.alice.handle_request(request)
        
        # Проверяем результат
        self.assertIsInstance(response, dict)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertIn('end_session', response)
        # Проверяем, что состояние изменилось на INITIATED
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')


if __name__ == '__main__':
    unittest.main() 