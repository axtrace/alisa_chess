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
        nlu = self.request.get('request', {}).get('nlu', {})
        return intent_name in nlu.get('intents', {})

    def restore_prev_state(self):
        """Восстанавливает предыдущее состояние игры."""
        self.game.restore_prev_state()
        return None

    def reset_game(self):
        """Сбрасывает игру."""
        self.game.reset_board()
        self.game.set_skill_state('INITIATED')
        return None

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say, lang='ru'):
        """Подготавливает текст для возврата в навык Алисы, чтобы озвучить ход."""
        text, text_tts = self.text_preparer.say_your_move(comp_move=comp_move, prev_turn=prev_turn, text_to_show=text_to_show, text_to_say=text_to_say)
        return text, text_tts
