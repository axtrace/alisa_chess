import texts
from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator


class WaitingConfirmHandler(BaseHandler):
    """Обработчик состояния ожидания подтверждения начала игры."""
    
    def __init__(self, game, request):
        super().__init__(game, request)
        self.validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания подтверждения."""
        print(f"WaitingConfirmHandler. handle. Запрос: {self.request}")
        if not self.validator.validate_yes():
            return self.say(texts.dng_start_text)
            
        self.game.set_skill_state('WAITING_COLOR')
        text, text_tts = self.text_preparer.say_choose_color()
        return self.say(text, tts=text_tts) 