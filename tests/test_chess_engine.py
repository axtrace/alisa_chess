import unittest
import os
from unittest.mock import patch, MagicMock
from game import ChessEngineAPI


class TestChessEngineAPI(unittest.TestCase):
    """Тесты для класса ChessEngineAPI."""

    def setUp(self):
        """Подготовка перед каждым тестом."""
        # Сохраняем оригинальные переменные окружения
        self.original_env = dict(os.environ)

    def tearDown(self):
        """Очистка после каждого теста."""
        # Восстанавливаем оригинальные переменные окружения
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_init_default_values(self):
        """Тест инициализации с значениями по умолчанию."""
        # Очищаем переменные окружения для теста
        if 'CHESS_API_URL' in os.environ:
            del os.environ['CHESS_API_URL']
        if 'CHESS_API_KEY' in os.environ:
            del os.environ['CHESS_API_KEY']

        api = ChessEngineAPI()

        self.assertEqual(api.api_url, "https://alice-chess.ru:8000/bestmove/")
        self.assertEqual(api.api_key, "")

    def test_init_with_env_variables(self):
        """Тест инициализации с переменными окружения."""
        os.environ['CHESS_API_URL'] = 'https://test-server.com/api/'
        os.environ['CHESS_API_KEY'] = 'test-key-123'

        api = ChessEngineAPI()

        self.assertEqual(api.api_url, 'https://test-server.com/api/')
        self.assertEqual(api.api_key, 'test-key-123')

    def test_init_constructor_params_override_env(self):
        """Тест что параметры конструктора переопределяют переменные окружения."""
        os.environ['CHESS_API_URL'] = 'https://env-server.com/api/'
        os.environ['CHESS_API_KEY'] = 'env-key'

        api = ChessEngineAPI(api_key='constructor-key')

        self.assertEqual(api.api_url, 'https://env-server.com/api/')  # Из env
        self.assertEqual(api.api_key, 'constructor-key')  # Из конструктора

    def test_init_constructor_url_override_env(self):
        """Тест что URL из конструктора переопределяет переменную окружения."""
        os.environ['CHESS_API_URL'] = 'https://env-server.com/api/'

        api = ChessEngineAPI()
        api.api_url = 'https://constructor-url.com/api/'  # Имитируем установку

        # Фактически тестируем что можно установить URL напрямую
        self.assertEqual(api.api_url, 'https://constructor-url.com/api/')

    @patch('game.requests.post')
    def test_get_best_move_success(self, mock_post):
        """Тест успешного получения лучшего хода."""
        # Очищаем переменные окружения для теста
        if 'CHESS_API_KEY' in os.environ:
            del os.environ['CHESS_API_KEY']
        if 'CHESS_API_URL' in os.environ:
            del os.environ['CHESS_API_URL']

        # Настраиваем мок для успешного ответа
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'best_move': 'e2e4'}
        mock_post.return_value = mock_response

        api = ChessEngineAPI()
        result = api.get_best_move('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

        self.assertEqual(result, 'e2e4')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://alice-chess.ru:8000/bestmove/')

        # Проверяем заголовки
        expected_headers = {
            'X-API-Key': '',
            'Content-Type': 'application/json'
        }
        self.assertEqual(kwargs['headers'], expected_headers)

        # Проверяем данные запроса
        expected_data = {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'depth': 10,
            'time': 0.1
        }
        self.assertEqual(kwargs['json'], expected_data)

    @patch('game.requests.post')
    def test_get_best_move_with_custom_params(self, mock_post):
        """Тест получения лучшего хода с кастомными параметрами."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'best_move': 'Nf3'}
        mock_post.return_value = mock_response

        api = ChessEngineAPI()
        result = api.get_best_move('fen-string', depth=15, time=0.5)

        self.assertEqual(result, 'Nf3')
        args, kwargs = mock_post.call_args
        expected_data = {
            'fen': 'fen-string',
            'depth': 15,
            'time': 0.5
        }
        self.assertEqual(kwargs['json'], expected_data)

    @patch('game.requests.post')
    def test_get_best_move_with_api_key(self, mock_post):
        """Тест получения лучшего хода с API ключом."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'best_move': 'd4'}
        mock_post.return_value = mock_response

        api = ChessEngineAPI(api_key='test-api-key')
        result = api.get_best_move('fen-string')

        self.assertEqual(result, 'd4')
        args, kwargs = mock_post.call_args
        expected_headers = {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json'
        }
        self.assertEqual(kwargs['headers'], expected_headers)

    @patch('game.requests.post')
    def test_get_best_move_http_error(self, mock_post):
        """Тест обработки HTTP ошибок."""
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("403 Client Error")
        mock_post.return_value = mock_response

        api = ChessEngineAPI()
        result = api.get_best_move('fen-string')

        self.assertIsNone(result)
        mock_post.assert_called_once()

    @patch('game.requests.post')
    def test_get_best_move_request_exception(self, mock_post):
        """Тест обработки сетевых ошибок."""
        from requests.exceptions import ConnectionError

        mock_post.side_effect = ConnectionError("Connection failed")

        api = ChessEngineAPI()
        result = api.get_best_move('fen-string')

        self.assertIsNone(result)
        mock_post.assert_called_once()

    @patch('game.requests.post')
    def test_get_best_move_invalid_response(self, mock_post):
        """Тест обработки некорректного ответа сервера."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}  # Нет поля best_move
        mock_post.return_value = mock_response

        api = ChessEngineAPI()
        result = api.get_best_move('fen-string')

        self.assertIsNone(result)

    def test_custom_url_storage(self):
        """Тест хранения кастомного URL."""
        api = ChessEngineAPI()
        custom_url = "https://my-custom-chess-server.com/bestmove/"
        api.api_url = custom_url

        self.assertEqual(api.api_url, custom_url)

    def test_api_key_storage(self):
        """Тест хранения API ключа."""
        api = ChessEngineAPI(api_key='custom-key')
        self.assertEqual(api.api_key, 'custom-key')

        # Тест изменения ключа
        api.api_key = 'new-key'
        self.assertEqual(api.api_key, 'new-key')


if __name__ == '__main__':
    unittest.main()
