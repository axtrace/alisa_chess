#!/usr/bin/env python3
"""
Скрипт для тестирования локального Flask-сервера Alice Chess.
Отправляет тестовые запросы на сервер для проверки функциональности.
"""

import requests
import json

def send_request(command, session_id="test-session", user_state=None):
    """Отправляет запрос на локальный сервер."""
    url = "http://localhost:5000/"

    data = {
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
            "session_id": session_id,
            "skill_id": "alice-chess-test",
            "user": {
                "user_id": "test-user-id"
            },
            "application": {
                "application_id": "test-app-id"
            },
            "user_id": "test-user-id",
            "skill_id": "alice-chess-test",
            "new": True,
            "message_id": 0
        },
        "request": {
            "command": command,
            "original_utterance": command,
            "type": "SimpleUtterance",
            "markup": {
                "dangerous_context": False
            },
            "payload": {},
            "nlu": {
                "tokens": command.split(),
                "entities": [],
                "intents": {}
            }
        },
        "version": "1.0"
    }

    if user_state:
        data["state"] = {"user": user_state}

    print(f"\nОтправка команды: '{command}'")
    print("-" * 50)

    try:
        response = requests.post(url, json=data)
        result = response.json()

        print(f"Ответ сервера:")
        print(f"TTS: {result['response']['tts']}")
        print(f"Text: {result['response']['text']}")
        print(f"End session: {result['response'].get('end_session', False)}")

        if 'user_state_update' in result and 'game_state' in result['user_state_update']:
            print(f"Game state: {result['user_state_update']['game_state']}")

        return result

    except Exception as e:
        print(f"Ошибка при отправке запроса: {e}")
        return None

def main():
    """Основная функция тестирования."""
    print("Тестирование локального сервера Alice Chess")
    print("=" * 50)

    # Тест 1: Начальный запрос
    result1 = send_request("Давай сыграем в шахматы")

    # Тест 2: Выбор цвета
    if result1 and 'user_state_update' in result1:
        game_state = result1['user_state_update']['game_state']
        result2 = send_request("Белые", user_state={'game_state': game_state})

        # Тест 3: Ход
        if result2 and 'user_state_update' in result2:
            game_state = result2['user_state_update']['game_state']
            result3 = send_request("е4", user_state={'game_state': game_state})

            # Тест 4: Показ доски
            if result3 and 'user_state_update' in result3:
                game_state = result3['user_state_update']['game_state']
                send_request("Покажи доску", user_state={'game_state': game_state})

    print("\n" + "=" * 50)
    print("Тестирование завершено!")

if __name__ == "__main__":
    main()
