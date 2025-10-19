#!/usr/bin/env python3
"""
Test script to verify the local chess engine fallback works.
"""

import requests
import json

def test_chess_game():
    """Test a complete chess game flow."""
    base_url = "http://localhost:5000"

    # Test server health
    print("Testing server health...")
    health = requests.get(f"{base_url}/health")
    if health.status_code != 200:
        print("❌ Server not responding")
        return
    print("✅ Server is running")

    # Start new game
    print("\nStarting new game...")
    response = send_command("Давай сыграем в шахматы")
    if not response:
        return

    # Choose white
    print("\nChoosing white pieces...")
    state = response['user_state_update']['game_state']
    response = send_command("Белые", state)
    if not response:
        return

    # Make first move
    print("\nMaking first move (e4)...")
    state = response['user_state_update']['game_state']
    response = send_command("е4", state)
    if not response:
        return

    print("✅ Game flow completed successfully!")
    print(f"Current board state: {response['user_state_update']['game_state']['board_state']}")
    print(f"Response text: {response['response']['text'][:200]}...")

def send_command(command, user_state=None):
    """Send a command to the server."""
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
            "session_id": "test-session-123",
            "skill_id": "alice-chess-test",
            "user": {
                "user_id": "test-user"
            },
            "application": {
                "application_id": "test-app"
            },
            "user_id": "test-user",
            "new": user_state is None,
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

    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error sending command '{command}': {e}")
        return None

if __name__ == "__main__":
    test_chess_game()
