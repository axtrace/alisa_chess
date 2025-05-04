import os

# API Settings
CHESS_API_URL = "https://alice-chess.ru:8000/bestmove/"
CHESS_API_KEY = os.getenv("CHESS_API_KEY", "")

# Game Settings
DEFAULT_SKILL_LEVEL = 1
DEFAULT_TIME_LEVEL = 0.1
DEFAULT_DEPTH = 10 