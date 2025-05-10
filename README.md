# alisa_chess

Игра в шахматы с голосовым управлением через Яндекс.Алису

## Возможности
- Голосовая игра в шахматы с Яндекс.Алисой
- Использование шахматного движка Stockfish 16
- Поддержка стандартной шахматной нотации
- Распознавание и синтез голоса
- Возможность развертывания через Flask или в serverless-режиме

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
- `alice_chess.py` - Основная логика игры
- `game.py` - Реализация шахматной игры
- `speaker.py` - Синтез голоса
- `text_preparer.py` - Обработка текста
- `move_extractor.py` - Парсинг шахматных ходов
- `request_parser.py` - Обработка запросов
- `alice_flask_server.py` - Реализация Flask-сервера
- `alice_serverless.py` - Serverless-развертывание

## Пример использования

```text
Алиса:
- Давайте сыграем в шахматы
Юзер:
- Да
Алиса:
- Е4. Ваш ход
Юзер:
- Е5
Алиса:
- Конь f3. Ваш ход
....
Алиса:
- Мат.
```

## Технические детали
- Шахматный движок Stockfish 16, поднят на отдельном сервере. Код сервера см. https://github.com/axtrace/chessapi.
- Используется: https://github.com/niklasf/python-chess
- Варианты развертывания: Serverless на Yandex Cloud

## Разработка
- Запуск тестов: `python -m pytest tests/`
- Проверка стиля кода: `flake8 .`
- Генерация документации: `cd docs && make html`

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
[Диаграммы](https://github.com/axtrace/alisa_chess/blob/69ef50d4f7dad2d828f633468e4566c297f6b164/docs/reqs/hi_seq_diag.md)

