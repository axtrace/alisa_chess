from flask import Flask, request, jsonify
from alice_chess import AliceChess
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальный экземпляр AliceChess для хранения состояния между запросами
alice_chess = AliceChess()

@app.route('/', methods=['POST'])
def handle_alice_request():
    """Обработчик запросов от Алисы."""
    try:
        # Получаем данные запроса
        data = request.get_json()
        logger.info(f"Получен запрос: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # Извлекаем состояние игры из состояния пользователя
        if 'state' in data and 'user' in data['state'] and 'game_state' in data['state']['user']:
            game_state = data['state']['user']['game_state']
            alice_chess.set_game_state(game_state)

        # Обрабатываем запрос
        response = alice_chess.handle_request(data)

        # Возвращаем ответ с обновленным состоянием
        result = {
            'version': '1.0',
            'session': data.get('session', {}),
            'response': response,
            'user_state_update': {
                'game_state': alice_chess.get_game_state()
            },
            'session_state': {
                'previous_response': response
            }
        }

        logger.info(f"Отправлен ответ: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}")
        error_response = {
            'version': '1.0',
            'session': request.get_json().get('session', {}),
            'response': {
                'tts': 'Произошла ошибка при обработке запроса',
                'text': f'Произошла ошибка при обработке запроса: {str(e)}',
                'end_session': True
            }
        }
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера."""
    return jsonify({'status': 'ok', 'message': 'Alice Chess server is running'})

if __name__ == '__main__':
    print("Запуск Flask-сервера для Alice Chess...")
    print("Сервер будет доступен по адресу: http://localhost:5000")
    print("Для тестирования отправляйте POST запросы на /")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
