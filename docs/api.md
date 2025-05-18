# API документация

## Основные эндпоинты

### 1. Обработчик навыка Алисы
```python
# alice_chess.py
def handler(event, context):
    """
    Основной обработчик для навыка Алисы.
    
    Args:
        event (dict): Событие от Алисы
        context (dict): Контекст выполнения
        
    Returns:
        dict: Ответ для Алисы
    """
```

### 2. Обработчик бессерверной функции
```python
# alice_serverless.py
def handler(event, context):
    """
    Обработчик для бессерверной функции Яндекс Облака.
    
    Args:
        event (dict): Событие от Яндекс Облака
        context (dict): Контекст выполнения
        
    Returns:
        dict: Ответ для Яндекс Облака
    """
```

## Основные классы

### 1. Игровая логика
```python
# game.py
class ChessGame:
    """
    Основной класс для управления шахматной игрой.
    
    Methods:
        make_move(move: str) -> bool: Сделать ход
        get_board_state() -> dict: Получить состояние доски
        is_game_over() -> bool: Проверить окончание игры
    """
```

### 2. Обработка ходов
```python
# move_extractor.py
class MoveExtractor:
    """
    Класс для обработки и валидации ходов.
    
    Methods:
        extract_move(text: str) -> str: Извлечь ход из текста
        validate_move(move: str) -> bool: Проверить корректность хода
    """
```

### 3. Генерация ответов
```python
# speaker.py
class Speaker:
    """
    Класс для генерации текстовых ответов.
    
    Methods:
        generate_response(game_state: dict) -> str: Сгенерировать ответ
        format_move(move: str) -> str: Отформатировать ход
    """
```

## Форматы данных

### 1. Входящий запрос
```json
{
    "version": "1.0",
    "session": {
        "session_id": "string",
        "user_id": "string"
    },
    "request": {
        "command": "string",
        "original_utterance": "string",
        "type": "string"
    }
}
```

### 2. Исходящий ответ
```json
{
    "version": "1.0",
    "session": {
        "session_id": "string",
        "user_id": "string"
    },
    "response": {
        "text": "string",
        "end_session": false
    }
}
```

## Обработка ошибок

### 1. Неверный ход
```python
{
    "response": {
        "text": "Ход невозможен. Попробуйте другой ход.",
        "end_session": false
    }
}
```

### 2. Неверный формат
```python
{
    "response": {
        "text": "Извините, я не поняла ваш ход. Пожалуйста, повторите.",
        "end_session": false
    }
}
```

## Примеры использования

### 1. Сделать ход
```python
game = ChessGame()
move = "e4"
if game.make_move(move):
    response = speaker.generate_response(game.get_board_state())
else:
    response = "Ход невозможен"
```

### 2. Проверить состояние игры
```python
if game.is_game_over():
    result = game.get_game_result()
    response = f"Игра окончена. Результат: {result}"
``` 