# alisa_chess

Игра в шахматы с голосовым управлением через Яндекс.Алису

## Возможности
- Голосовая игра в шахматы с Яндекс.Алисой
- Использование шахматного движка Stockfish 16
- Поддержка стандартной шахматной и SAN нотации, включая кириллицу
- Распознавание и синтез голоса
- Восстановление состояния между запросами (state management)
- Поддержка интентов Алисы: помощь, новая игра, сдача, ничья и др.
- Возможность развертывания через Flask или в serverless-режиме
- Поддержка превращения пешек
- Поддержка предложения и принятия ничьей
- Поддержка сдачи партии

## Специальные команды
Следующие команды доступны в любой момент игры:
- "Помощь" - показать справку по игре
- "Покажи доску" - отобразить текущую позицию
- "Новая игра" - начать новую партию
- "Уровень сложности" - изменить уровень игры
- "Ничья" - предложить ничью
- "Сдаюсь" - сдаться

## Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/axtrace/alisa_chess.git
cd alisa_chess
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Для Windows: .venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Структура проекта
- `alice_chess.py` — Основная логика навыка
- `game.py` — Логика шахматной партии и состояния
- `handlers/` — Обработчики состояний навыка (инициализация, ход, подтверждения и т.д.)
- `request_validators/` — Валидаторы интентов и команд пользователя
- `move_extractor.py` — Парсинг шахматных ходов (алгебраическая/SAN/кириллица)
- `speaker.py` — Синтез голоса
- `text_preparer.py` — Обработка текста
- `alice_flask_server.py` — Реализация Flask-сервера
- `alice_serverless.py` — Serverless-развертывание
- `tests/` — Юнит-тесты для всех ключевых компонентов
- `diagrams/` — Диаграммы состояний и последовательности

## Пример использования

```text
Алиса:
- Давайте сыграем в шахматы
Юзер:
- Да
Алиса:
- За какую сторону вы хотите играть? Белые или черные?
Юзер:
- Белые
Алиса:
- Е4. Ваш ход
Юзер:
- Покажи доску
Алиса:
- [показывает текущую позицию]
Юзер:
- Е5
Алиса:
- Конь f3. Ваш ход
...
Алиса:
- Мат.
```

## Пример внутренностей запроса от Алисы к навыку с восстановлением состояния
```json
{
  "request": {"command": "e2e4", ...},
  "state": {
    "user": {
      "game_state": {
        "board_state": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "skill_state": "WAITING_MOVE",
        "user_color": "WHITE",
        "skill_level": 1,
        "time_level": 0.1
      }
    }
  }
}
```

## Тестирование
- Запуск всех тестов:
  ```bash
  python -m unittest discover tests
  ```

## Технические детали
- Шахматный движок Stockfish 16, поднят на отдельном сервере. Код сервера см. https://github.com/axtrace/chessapi.
- Используется: https://github.com/niklasf/python-chess
- Варианты развертывания: Serverless на Yandex Cloud

## Архитектура
- Навык построен на классах AliceChess (основная логика), Game (шахматная партия), обработчиках состояний (handlers), валидаторах интентов (request_validators).
- Вся логика переходов между состояниями описана в [диаграмме состояний](diagrams/state_diagram.md).
- Подробная последовательность обработки запросов описана в [диаграмме последовательности](diagrams/sd_request_processing.md).
- Специальные команды (помощь, показ доски и т.д.) обрабатываются независимо от текущего состояния игры через SpecialIntentHandler.

## Участие в разработке
Мы приветствуем участие в разработке! Вы можете отправить Pull Request.

## Лицензия
MIT License

Copyright (c) 2024 axtrace

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Дополнительно
[Диаграммы](docs/diagrams/readme.md)

