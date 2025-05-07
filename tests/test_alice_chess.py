import unittest
from unittest.mock import patch, MagicMock
from alice_chess import AliceChess


class TestAliceChess(unittest.TestCase):
    """Тесты для класса AliceChess."""
    
    def setUp(self):
        """Подготовка базового запроса для тестов."""
        self.event = {
            "meta": {
                "locale": "ru-RU",
                "timezone": "UTC",
                "client_id": "ru.yandex.searchplugin/7.16",
                "interfaces": {
                    "screen": {},
                    "payments": {},
                    "account_linking": {}
                }
            },
            "session": {
                "message_id": 0,
                "session_id": "test-session-id",
                "skill_id": "test-skill-id",
                "user": {
                    "user_id": "test-user-id"
                },
                "application": {
                    "application_id": "test-app-id"
                },
                "user_id": "test-user-id",
                "new": True
            },
            "request": {
                "command": "",
                "original_utterance": "",
                "nlu": {
                    "tokens": [],
                    "entities": [],
                    "intents": {}
                },
                "markup": {
                    "dangerous_context": False
                },
                "type": "SimpleUtterance"
            },
            "state": {
                "session": {},
                "user": {},
                "application": {}
            },
            "version": "1.0"
        }
        self.alice = AliceChess(self.event)

    def test_init(self):
        """Тест инициализации класса."""
        self.assertIsNotNone(self.alice)
        self.assertEqual(self.alice.game.get_skill_state(), 'INITIATED')

    def test_handle_request_initiated_state(self):
        """Тест обработки запроса в начальном состоянии."""
        response = self.alice.handle_request(self.event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])

    @patch('game.Game')
    def test_handle_request_waiting_move(self, mock_game):
        """Тест обработки запроса в состоянии ожидания хода."""
        # Настраиваем мок для игры
        mock_game_instance = MagicMock()
        mock_game_instance.get_skill_state.return_value = 'WAITING_MOVE'
        mock_game_instance.is_valid_move.return_value = True
        mock_game.return_value = mock_game_instance
        
        # Создаем новый экземпляр AliceChess с моком
        alice = AliceChess(self.event)
        
        # Создаем запрос с ходом
        event = self.event.copy()
        event['request']['command'] = 'e2e4'
        event['request']['original_utterance'] = 'e2e4'
        
        response = alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])

    def test_handle_request_invalid_state(self):
        """Тест обработки запроса с недопустимым состоянием."""
        self.alice.game.set_skill_state('INVALID_STATE')
        with self.assertRaises(ValueError):
            self.alice.handle_request(self.event)

    def test_handle_request_help_intent(self):
        """Тест обработки запроса с намерением помощи."""
        # Создаем запрос с намерением помощи
        event = self.event.copy()
        event['request']['nlu']['intents'] = {'help': {}}
        
        response = self.alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])
        self.assertIn('помощь', response['text'].lower())

    def test_handle_request_new_game_intent(self):
        """Тест обработки запроса с намерением новой игры."""
        # Создаем запрос с намерением новой игры
        event = self.event.copy()
        event['request']['nlu']['intents'] = {'new_game': {}}
        
        response = self.alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])
        self.assertEqual(self.alice.game.get_skill_state(), 'WAITING_CONFIRM')


if __name__ == '__main__':
    unittest.main() 