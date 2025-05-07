from abc import ABC, abstractmethod
from game import Game
from speaker import Speaker
from text_preparer import TextPreparer


class BaseHandler(ABC):
    """Базовый класс для обработчиков состояний."""
    
    def __init__(self, game: Game, request: dict):
        self.game = game
        self.request = request
        self.speaker = Speaker()
        self.text_preparer = TextPreparer()

    def say(self, text, tts=None, end_session=False):
        """Формирует ответ в формате Яндекс Диалогов."""
        return {
            'text': text,
            'tts': tts or text,
            'end_session': end_session
        }

    @abstractmethod
    def handle(self):
        """Обрабатывает запрос в текущем состоянии."""
        pass

    def _has_intent(self, intent_name):
        """Проверяет наличие интента в запросе."""
        if not all(key in self.request.get('request', {}) for key in ['nlu', 'intents']):
            return False
        return intent_name in self.request['request']['nlu']['intents']

    def _has_text(self, list_of_words):
        """Проверяет текстовое совпадение с словами."""
        command = self.request.get('request', {}).get('command', '').lower()
        return command in list_of_words 
    
    def restore_prev_state(self):
        """Восстанавливает предыдущее состояние игры."""
        prev_state = self.request['state']['user']['game_state']['prev_state']
        self.game.set_skill_state(prev_state)
        return None
    
    def reset_game(self):
        """Сбрасывает игру."""
        self.game.board.reset()
        self.game.set_skill_state('INITIATED')
        return None