import unittest
from request_validators.intent_validator import IntentValidator


class TestValidators(unittest.TestCase):
    """Тесты для валидаторов запросов."""
    
    def setUp(self):
        """Подготовка окружения для тестов."""
        self.validator = IntentValidator({})
        
    def test_validate_yes(self):
        """Тест валидации положительного ответа."""
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
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_yes())
        
    def test_validate_no(self):
        """Тест валидации отрицательного ответа."""
        request = {
            'request': {
                'command': 'нет',
                'nlu': {
                    'intents': {
                        'YANDEX.REJECT': {}
                    }
                }
            }
        }
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_no())
        
    def test_validate_help(self):
        """Тест валидации запроса помощи."""
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
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_help())
        
    def test_validate_draw(self):
        """Тест валидации предложения ничьей."""
        request = {
            'request': {
                'command': 'ничья',
                'nlu': {
                    'intents': {
                        'DRAW': {}
                    }
                }
            }
        }
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_draw())
        
    def test_validate_resign(self):
        """Тест валидации сдачи."""
        request = {
            'request': {
                'command': 'сдаюсь',
                'nlu': {
                    'intents': {
                        'RESIGN': {}
                    }
                }
            }
        }
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_resign())
        
    def test_validate_new_game(self):
        """Тест валидации запроса новой игры."""
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
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_new_game())
        
    def test_validate_unmake(self):
        """Тест валидации отмены хода."""
        request = {
            'request': {
                'command': 'отменить ход',
                'nlu': {
                    'intents': {
                        'UNMAKE': {}
                    }
                }
            }
        }
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_unmake())
        
    def test_validate_repeat_last_move(self):
        """Тест валидации повтора последнего хода."""
        request = {
            'request': {
                'command': 'повторить ход',
                'nlu': {
                    'intents': {
                        'REPEAT_LAST_MOVE': {}
                    }
                }
            }
        }
        validator = IntentValidator(request)
        self.assertTrue(validator.validate_repeat_last_move())
        
    def test_validate_general(self):
        """Тест общей валидации."""
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
        validator = IntentValidator(request)
        self.assertTrue(validator.validate())


if __name__ == '__main__':
    unittest.main()