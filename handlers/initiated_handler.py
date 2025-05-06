import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class InitiatedHandler(BaseHandler):
    """Обработчик начального состояния."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в начальном состоянии."""
        self.game.set_skill_state('WAITING_CONFIRM')
        return self.say(texts.hi_text, tts=texts.hi_text) 