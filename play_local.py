#!/usr/bin/env python3
"""
Интерактивная игра в шахматы через локальный сервер Alice Chess.
Позволяет играть в шахматы, вводя команды в консоли.
"""

import requests
import json
import sys

class AliceChessClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        self.session_id = "local-session-" + str(hash(self))
        self.user_state = None

    def send_command(self, command):
        """Отправляет команду на сервер и возвращает ответ."""
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
                "session_id": self.session_id,
                "skill_id": "alice-chess-local",
                "user": {
                    "user_id": "local-user"
                },
                "application": {
                    "application_id": "local-app"
                },
                "user_id": "local-user",
                "skill_id": "alice-chess-local",
                "new": self.user_state is None,
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

        if self.user_state:
            data["state"] = {"user": self.user_state}

        try:
            response = requests.post(self.server_url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Сохраняем состояние для следующего запроса
            if 'user_state_update' in result and 'game_state' in result['user_state_update']:
                self.user_state = {'game_state': result['user_state_update']['game_state']}

            return result
        except requests.exceptions.RequestException as e:
            print(f"Ошибка соединения с сервером: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Ошибка обработки ответа сервера: {e}")
            return None

    def play(self):
        """Интерактивная игра."""
        print("=" * 60)
        print("🎯 ИГРА В ШАХМАТЫ С АЛИСОЙ (ЛОКАЛЬНАЯ ВЕРСИЯ)")
        print("=" * 60)
        print("Введите команды на русском языке.")
        print("Доступные команды:")
        print("• 'Давай сыграем в шахматы' - начать игру")
        print("• 'Белые' или 'Черные' - выбрать цвет")
        print("• Шахматные ходы (е2е4, Кf3, О-О и т.д.)")
        print("• 'Покажи доску' - показать текущую позицию")
        print("• 'Новая игра' - начать новую партию")
        print("• 'Помощь' - показать справку")
        print("• 'Сдаюсь' - сдаться")
        print("• 'Ничья' - предложить ничью")
        print("• 'Уровень сложности' - изменить уровень")
        print("• 'выход' или 'quit' - выйти")
        print("-" * 60)

        while True:
            try:
                user_input = input("\n👤 Ваш ход: ").strip()

                if user_input.lower() in ['выход', 'quit', 'exit', 'q']:
                    print("👋 До свидания!")
                    break

                if not user_input:
                    continue

                print("🤖 Алиса думает...")
                response = self.send_command(user_input)

                if response:
                    print(f"🎤 {response['response']['tts']}")
                    if response['response']['text'] != response['response']['tts']:
                        print(f"📝 {response['response']['text']}")

                    # Если игра окончена, показываем результат
                    if response['response'].get('end_session', False):
                        print("\n🏁 Игра окончена!")
                        choice = input("Хотите сыграть еще раз? (да/нет): ").strip().lower()
                        if choice in ['да', 'yes', 'y', 'д']:
                            self.user_state = None  # Сбрасываем состояние
                            print("Начинаем новую игру...")
                            continue
                        else:
                            break
                else:
                    print("❌ Не удалось получить ответ от сервера")

            except KeyboardInterrupt:
                print("\n👋 Игра прервана пользователем")
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")

def main():
    """Основная функция."""
    client = AliceChessClient()

    # Проверяем, что сервер работает
    try:
        health_response = requests.get("http://localhost:5000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Сервер Alice Chess работает")
        else:
            print("❌ Сервер не отвечает корректно")
            return
    except requests.exceptions.RequestException:
        print("❌ Не удается подключиться к серверу Alice Chess")
        print("Убедитесь, что сервер запущен: python alice_flask_server.py")
        return

    # Запускаем игру
    client.play()

if __name__ == "__main__":
    main()
