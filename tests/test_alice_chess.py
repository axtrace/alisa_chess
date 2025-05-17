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
        self.alice = AliceChess()

    def test_init(self):
        """Тест инициализации класса."""
        self.alice.handle_request(self.event)
        self.assertIsNotNone(self.alice.game)
        self.assertEqual(self.alice.game.get_skill_state(), 'WAITING_CONFIRM')

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
        
        alice = AliceChess()
        event = self.event.copy()
        event['request']['command'] = 'e2e4'
        event['request']['original_utterance'] = 'e2e4'
        response = alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])

    @patch('game.Game')
    def test_handle_request_waiting_move_invalid(self, mock_game):
        """Тест обработки запроса с некорректным ходом в состоянии ожидания хода."""
        # Настраиваем мок для игры
        mock_game_instance = MagicMock()
        mock_game_instance.get_skill_state.return_value = 'WAITING_MOVE'
        mock_game_instance.is_valid_move.return_value = False
        mock_game.return_value = mock_game_instance
        
        alice = AliceChess()
        # Устанавливаем состояние игры в WAITING_MOVE
        alice.game = mock_game_instance
        print(f"alice.game.get_skill_state(): {alice.game.get_skill_state()}")
        
        event = self.event.copy()
        event['request']['command'] = 'д2д5'  # Некорректный ход
        event['request']['original_utterance'] = 'д2д5'
        event['state']['user']['game_state'] = {'skill_state': 'WAITING_MOVE'}
        response = alice.handle_request(event)
        
        # Проверяем, что ответ содержит сообщение об ошибке
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])
        self.assertIn('невозможен', response['text'].lower() or 'недопустимый ход', response['text'].lower())

    def test_handle_request_help_intent(self):
        """Тест обработки запроса с намерением помощи."""
        event = self.event.copy()
        event['request']['nlu']['intents'] = {'help': {}}
        response = self.alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])
        self.assertIn('помощь', response['text'].lower())

    def test_handle_request_new_game_intent(self):
        """Тест обработки запроса с намерением новой игры."""
        event = self.event.copy()
        event['request']['nlu']['intents'] = {'NEW_GAME': {}}
        response = self.alice.handle_request(event)
        self.assertIn('text', response)
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])
        self.assertEqual(self.alice.game.get_skill_state(), 'WAITING_NEWGAME_CONFIRM')

    @patch('game.Game')
    def test_handle_request_promotion(self, mock_game):
        """Тест обработки запроса с превращением пешки."""
        # Настраиваем мок для игры
        mock_game_instance = MagicMock()
        mock_game_instance.get_skill_state.return_value = 'WAITING_MOVE'
        mock_game_instance.is_valid_move.return_value = True
        
        # Настраиваем user_move
        def mock_user_move(move):
            return True
        mock_game_instance.user_move.side_effect = mock_user_move
        
        # Настраиваем who для возврата текущего хода
        mock_game_instance.who.return_value = 'White'
        
        # Настраиваем comp_move для возврата хода компьютера
        mock_game_instance.comp_move.return_value = 'e7e5'
        
        # Настраиваем get_board для возврата доски
        mock_game_instance.get_board.return_value = '8/P7/8/7k/8/8/8/2K5 w - - 0 1'
        
        mock_game.return_value = mock_game_instance
        
        alice = AliceChess()
        alice.game = mock_game_instance
        
        # Тестируем ход с превращением пешки
        event = self.event.copy()
        event['request']['command'] = 'а8'
        event['request']['original_utterance'] = 'а8'
        event['request']['nlu'] = {
            'tokens': ['пешка', 'a', '8', 'ладья'],
            'entities': [],
            'intents': {
                'CHESS_MOVE': {
                    'slots': {
                        'piece': {
                            'type': 'ChessPiece',
                            'tokens': {'start': 0, 'end': 1},
                            'value': 'pawn'
                        },
                        'file_to': {
                            'type': 'ChessFile',
                            'tokens': {'start': 1, 'end': 2},
                            'value': 'a'
                        },
                        'rank_to': {
                            'type': 'ChessRank',
                            'tokens': {'start': 2, 'end': 3},
                            'value': '8'
                        },
                        'promotion_piece': {
                            'type': 'ChessPiece',
                            'tokens': {'start': 3, 'end': 4},
                            'value': 'rook'
                        }
                    }
                }
            }
        }
        event['state']['user'] = {
            'game_state': {
                'board_state': '8/P7/8/7k/8/8/8/2K5 w - - 0 1',
                'skill_state': 'WAITING_MOVE',
                'prev_skill_state': 'WAITING_MOVE',
                'user_color': 'WHITE',
                'comp_color': 'BLACK',
                'current_turn': 'White'
            }
        }
        
        # Добавляем отладочную информацию
        print("Before handle_request:")
        print(f"Game state: {mock_game_instance.get_skill_state()}")
        
        
        response = alice.handle_request(event)
        
        # Добавляем отладочную информацию
        print("After handle_request:")
        print(f"Game state: {mock_game_instance.get_skill_state()}")
        print(f"set_skill_state calls: {mock_game_instance.set_skill_state.call_args_list}")
        
        # Проверяем ответ
        self.assertIn('text', response)
        self.assertIn('♖', response['text'].lower())
        self.assertIn('tts', response)
        self.assertFalse(response['end_session'])


if __name__ == '__main__':
    unittest.main() 