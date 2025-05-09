import unittest
from unittest.mock import patch, MagicMock
from alice_serverless import handler


class TestServerless(unittest.TestCase):
    """Тесты для обработчика запросов от Алисы."""
    
    def setUp(self):
        """Подготовка базового запроса для тестов."""
        self.base_event = {
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

    def test_new_session(self):
        """Тест обработки нового сеанса."""
        with patch('alice_serverless.AliceChess') as mock_alice:
            # Настраиваем мок
            mock_instance = mock_alice.return_value
            mock_instance.handle_request.return_value = {
                'text': '\nДавайте сыграем в шахматы вслепую.\nХоды объявляются устно.\nДля начала игры скажите \'Да\'\nЕсли хотите узнать больше, скажите \'Помощь\'\n',
                'tts': '\nДавайте сыграем в шахматы вслепую.\nХоды объявляются устно.\nДля начала игры скажите \'Да\'\nЕсли хотите узнать больше, скажите \'Помощь\'\n',
                'end_session': False
            }
            mock_instance.get_game_state.return_value = {
                'board_state': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'skill_state': 'WAITING_CONFIRM',
                'prev_skill_state': '',
                'user_color': '',
                'comp_color': '',
                'attempts': 0,
                'current_turn': 'White'
            }
            
            # Вызываем обработчик
            response = handler(self.base_event, None)
            
            # Проверяем результат
            self.assertEqual(response['version'], '1.0')
            self.assertEqual(response['session'], self.base_event['session'])
            self.assertEqual(response['response'], {
                'text': '\nДавайте сыграем в шахматы вслепую.\nХоды объявляются устно.\nДля начала игры скажите \'Да\'\nЕсли хотите узнать больше, скажите \'Помощь\'\n',
                'tts': '\nДавайте сыграем в шахматы вслепую.\nХоды объявляются устно.\nДля начала игры скажите \'Да\'\nЕсли хотите узнать больше, скажите \'Помощь\'\n',
                'end_session': False
            })
            self.assertIn('user_state_update', response)
            self.assertIn('game_state', response['user_state_update'])
            
            # Проверяем, что AliceChess был вызван без параметров
            mock_alice.assert_called_once_with()
            mock_instance.handle_request.assert_called_once_with(self.base_event)

    def test_existing_session(self):
        """Тест обработки существующего сеанса."""
        # Добавляем состояние игры в запрос
        event = self.base_event.copy()
        event['state']['user'] = {
            'game_state': {
                'board_state': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'skill_state': 'WAITING_MOVE',
                'prev_skill_state': '',
                'user_color': '',
                'comp_color': '',
                'attempts': 0,
                'current_turn': 'Black'
            }
        }
        
        with patch('alice_serverless.AliceChess') as mock_alice:
            # Настраиваем мок
            mock_instance = mock_alice.return_value
            mock_instance.handle_request.return_value = {
                'text': '\nПростите, я не смогла понять ваш ход из фразы: \'{}\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'tts': '\nПростите, я не смогла понять ваш ход из фразы: \'{}\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'end_session': False
            }
            mock_instance.get_game_state.return_value = {
                'board_state': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
                'skill_state': 'WAITING_MOVE',
                'prev_skill_state': '',
                'user_color': '',
                'comp_color': '',
                'attempts': 0,
                'current_turn': 'Black'
            }
            
            # Вызываем обработчик
            response = handler(event, None)
            
            # Проверяем результат
            self.assertEqual(response['version'], '1.0')
            self.assertEqual(response['session'], event['session'])
            self.assertEqual(response['response'], {
                'text': '\nПростите, я не смогла понять ваш ход из фразы: \'{}\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'tts': '\nПростите, я не смогла понять ваш ход из фразы: \'{}\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'end_session': False
            })
            self.assertIn('user_state_update', response)
            self.assertIn('game_state', response['user_state_update'])
            
            # Проверяем, что AliceChess был вызван без параметров
            mock_alice.assert_called_once_with()
            mock_instance.handle_request.assert_called_once_with(event)

    def test_error_handling(self):
        """Тест обработки ошибок."""
        with patch('alice_serverless.AliceChess') as mock_alice:
            # Настраиваем мок для выброса исключения
            mock_alice.side_effect = Exception("Test error")
            
            # Вызываем обработчик
            response = handler(self.base_event, None)
            
            # Проверяем результат
            self.assertEqual(response['version'], '1.0')
            self.assertEqual(response['session'], self.base_event['session'])
            self.assertEqual(response['response'], {
                'tts': 'Произошла ошибка при обработке запроса',
                'text': 'Произошла ошибка при обработке запроса: Test error',
                'end_session': True
            })

    def test_move_handling(self):
        """Тест обработки хода."""
        # Создаем запрос с ходом
        event = self.base_event.copy()
        event['request']['command'] = 'e2e4'
        event['request']['original_utterance'] = 'e2e4'
        event['state']['user'] = {
            'game_state': {
                'board_state': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'skill_state': 'WAITING_MOVE',
                'prev_skill_state': '',
                'user_color': '',
                'comp_color': '',
                'attempts': 0,
                'current_turn': 'White'
            }
        }
        
        with patch('alice_serverless.AliceChess') as mock_alice:
            # Настраиваем мок
            mock_instance = mock_alice.return_value
            mock_instance.handle_request.return_value = {
                'text': '\nПростите, я не смогла понять ваш ход из фразы: \'e2e4\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'tts': '\nПростите, я не смогла понять ваш ход из фразы: \'e2e4\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'end_session': False
            }
            mock_instance.get_game_state.return_value = {
                'board_state': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'skill_state': 'WAITING_MOVE',
                'prev_skill_state': '',
                'user_color': '',
                'comp_color': '',
                'attempts': 0,
                'current_turn': 'White'
            }
            
            # Вызываем обработчик
            response = handler(event, None)
            
            # Проверяем результат
            self.assertEqual(response['version'], '1.0')
            self.assertEqual(response['session'], event['session'])
            self.assertEqual(response['response'], {
                'text': '\nПростите, я не смогла понять ваш ход из фразы: \'e2e4\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'tts': '\nПростите, я не смогла понять ваш ход из фразы: \'e2e4\'.\nПовторите, пожалуйста.\nСкажите \'Помощь\', если возникают проблемы с распознаванием.\n',
                'end_session': False
            })
            self.assertIn('user_state_update', response)
            self.assertIn('game_state', response['user_state_update'])
            
            # Проверяем, что состояние игры обновилось
            self.assertEqual(
                response['user_state_update']['game_state']['board_state'],
                'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            ) 