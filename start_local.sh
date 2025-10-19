#!/bin/bash

echo "🎯 Запуск Alice Chess"
echo "===================="

# Функция для отображения справки
show_help() {
    echo "Использование: $0 [ОПЦИИ]"
    echo ""
    echo "Опции:"
    echo "  --help, -h          Показать эту справку"
    echo "  --url URL           URL Chess API сервера (по умолчанию: http://localhost:8000/bestmove/)"
    echo "  --key KEY           API ключ для аутентификации (по умолчанию: локальный ключ)"
    echo "  --remote            Использовать удаленный сервер alice-chess.ru"
    echo ""
    echo "Переменные окружения:"
    echo "  PROJECT_ROOT        Путь к корневой директории проекта Alice Chess (по умолчанию: директория скрипта)"
    echo "  CHESSAPI_DIR        Путь к директории Chess API проекта (по умолчанию: ../chessapi)"
    echo "  CHESSAPI_VENV       Имя виртуального окружения Chess API (по умолчанию: chessapi_env)"
    echo ""
    echo "Примеры:"
    echo "  $0                           # Локальный сервер по умолчанию"
    echo "  $0 --remote                 # Удаленный сервер alice-chess.ru"
    echo "  $0 --url https://my-server.com/bestmove/ --key my-key"
    echo "  PROJECT_ROOT=/path/to/alice-chess $0  # Указать кастомный путь к проекту"
    echo ""
}

# Загрузка переменных окружения из .env файла
if [ -f ".env" ]; then
    echo "🔧 Загрузка переменных из .env файла..."
    set -a
    source .env
    set +a
fi

# Парсинг аргументов командной строки (с fallback значениями из .env)
CHESS_API_URL="${CHESS_API_URL:-http://localhost:8000/bestmove/}"
CHESS_API_KEY="${CHESS_API_KEY:-}"

# Настройки путей (с fallback значениями)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"
CHESSAPI_DIR="${CHESSAPI_DIR:-$(dirname "$PROJECT_ROOT")/chessapi}"
CHESSAPI_VENV="${CHESSAPI_VENV:-chessapi_env}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --url)
            CHESS_API_URL="$2"
            shift 2
            ;;
        --key)
            CHESS_API_KEY="$2"
            shift 2
            ;;
        --remote)
            CHESS_API_URL="https://alice-chess.ru:8000/bestmove/"
            CHESS_API_KEY="${CHESS_API_KEY:-}"  # Очистить ключ для удаленного сервера
            shift
            ;;
        *)
            echo "❌ Неизвестный параметр: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Определяем путь к активации виртуального окружения в зависимости от ОС
get_venv_activate_path() {
    local venv_dir="$1"
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "$venv_dir/Scripts/activate"
    else
        echo "$venv_dir/bin/activate"
    fi
}

# Проверяем виртуальное окружение
if [ ! -d "env" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его командой: python -m venv env"
    exit 1
fi

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
VENV_ACTIVATE_PATH=$(get_venv_activate_path "env")
source "$VENV_ACTIVATE_PATH"

# Экспортируем переменные окружения
export CHESS_API_URL
export CHESS_API_KEY

echo "🎯 Настройки Chess API:"
echo "   URL: $CHESS_API_URL"
if [ -n "$CHESS_API_KEY" ]; then
    echo "   Key: ${CHESS_API_KEY:0:10}..."
else
    echo "   Key: не установлен (для удаленного сервера)"
fi

# Проверяем и запускаем локальный Stockfish сервер (только для локального режима)
if [[ "$CHESS_API_URL" == http://localhost:8000/bestmove/ ]]; then
    echo "♟️ Проверка локального Stockfish сервера..."
    if ! curl -s http://localhost:8000/healthcheck -H "X-API-Key: $CHESS_API_KEY" > /dev/null 2>&1; then
        echo "Запуск локального Stockfish сервера..."
        if [ -d "$CHESSAPI_DIR" ]; then
            cd "$CHESSAPI_DIR"
            if [ -d "$CHESSAPI_VENV" ]; then
                CHESSAPI_VENV_ACTIVATE_PATH=$(get_venv_activate_path "$CHESSAPI_VENV")
                source "$CHESSAPI_VENV_ACTIVATE_PATH"
                python -m uvicorn chessapi:app --host 0.0.0.0 --port 8000 &
                CHESSAPI_PID=$!
                cd "$PROJECT_ROOT"
                echo "✅ Stockfish сервер запущен (PID: $CHESSAPI_PID)"
            else
                echo "❌ Виртуальное окружение Chess API не найдено: $CHESSAPI_DIR/$CHESSAPI_VENV"
                echo "Создайте его командой: cd $CHESSAPI_DIR && python -m venv $CHESSAPI_VENV"
                exit 1
            fi
        else
            echo "❌ Директория Chess API не найдена: $CHESSAPI_DIR"
            echo "Установите Chess API проект или укажите правильный путь через переменную CHESSAPI_DIR"
            exit 1
        fi
    else
        echo "✅ Stockfish сервер уже работает"
    fi
else
    echo "🌐 Используется внешний Chess API сервер: $CHESS_API_URL"
fi

# Проверяем зависимости
echo "📦 Проверка зависимостей..."
python -c "import alice_chess, chess, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Установка зависимостей..."
    pip install -r requirements.txt
fi

# Запускаем сервер в фоне
echo "🚀 Запуск Flask-сервера..."
python alice_flask_server.py &
SERVER_PID=$!

# Ждем запуска сервера
sleep 3

# Проверяем, что сервер запустился
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Сервер запущен успешно!"
    echo ""
    echo "🎮 Как играть:"
    echo "=============="
    echo "1. Откройте новый терминал"
    echo "2. Перейдите в папку проекта: cd $PROJECT_ROOT"
    echo "3. Активируйте окружение: source env/bin/activate"
    echo "4. Запустите игру: python play_local.py"
    echo ""
    echo "📋 Доступные команды:"
    echo "- 'Давай сыграем в шахматы' - начать игру"
    echo "- 'Белые' или 'Черные' - выбрать цвет"
    echo "- Шахматные ходы (е2е4, Кf3, О-О и т.д.)"
    echo "- 'Покажи доску' - показать текущую позицию"
    echo "- 'Новая игра' - начать новую партию"
    echo "- 'Помощь' - показать справку"
    echo "- 'Сдаюсь' - сдаться"
    echo "- 'Ничья' - предложить ничью"
    echo "- 'Уровень сложности' - изменить уровень"
    echo "- 'выход' или 'quit' - выйти"
    echo ""
    echo "🛑 Для остановки сервера нажмите Ctrl+C"
    echo ""
    echo "Сервер работает на: http://localhost:5000"
    echo "PID сервера: $SERVER_PID"
    echo ""

    # Ждем завершения
    wait $SERVER_PID
else
    echo "❌ Сервер не запустился!"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi
