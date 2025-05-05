from alice_serverless import handler

# Тестовый запрос для начала игры
test_event = {
    'version': '1.0',
    'session': {
        'new': True,
        'session_id': 'test_session',
        'user_id': 'test_user'
    },
    'request': {
        'command': 'давай поиграем в шахматы',
        'original_utterance': 'давай поиграем в шахматы'
    },
    'state': {
        'session': {}
    }
}

# Запускаем обработчик
response = handler(test_event, None)
print("Response:", response) 