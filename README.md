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
- Шахматный движок: Stockfish 16
- Используется: https://github.com/niklasf/python-chess
- Варианты развертывания: Serverless

## Разработка
- Запуск тестов: `python -m pytest tests/`
- Проверка стиля кода: `flake8 .`
- Генерация документации: `cd docs && make html`

## Участие в разработке
Мы приветствуем участие в разработке! Вы можете отправить Pull Request.

## Лицензия
[Укажите вашу лицензию здесь]

## Дополнительно
[Диаграммы](https://github.com/axtrace/alisa_chess/blob/69ef50d4f7dad2d828f633468e4566c297f6b164/docs/reqs/hi_seq_diag.md)

