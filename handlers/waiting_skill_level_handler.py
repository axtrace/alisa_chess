from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import texts

class WaitingSkillLevelHandler(BaseHandler):
    """Обработчик состояния ожидания выбора уровня сложности."""

    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)
        # Stockfish поддерживает уровни от 0 до 20
        self.min_level = 0
        self.max_level = 20

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания выбора уровня сложности."""

        # Проверяем отказ
        if self.intent_validator.validate_no():
            # Возвращаемся в предыдущее состояние
            self.game.set_skill_state(self.game.get_prev_skill_state())
            return self.say(texts.skill_level_cancel_text)

        # Проверяем числовой уровень сложности
        try:
            level = int(self.request['request']['command'])
            if self.min_level <= level <= self.max_level:
                self.game.set_skill_level(level)
                self.game.restore_prev_state()
                state_text = texts.state_texts.get(self.game.get_skill_state(), '')
                return self.say(texts.skill_level_changed_text.format(level=level) + '\n' + state_text)
            else:
                return self.say(texts.skill_level_invalid_text)
        except ValueError:
            return self.say(texts.skill_level_invalid_text)