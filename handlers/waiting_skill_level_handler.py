from .base_handler import BaseHandler
from request_validators.intent_validator import IntentValidator
import texts
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WaitingSkillLevelHandler(BaseHandler):
    """Обработчик состояния ожидания выбора уровня сложности."""

    # Stockfish поддерживает уровни от 0 до 20
    MIN_LEVEL = 0
    MAX_LEVEL = 20

    def __init__(self, game, request):
        super().__init__(game, request)
        self.intent_validator = IntentValidator(request)

    def handle(self):
        """Обрабатывает запрос в состоянии ожидания выбора уровня сложности."""
        logger.info(f"WaitingSkillLevelHandler.handle. Запрос: {self.request}")

        # Проверяем отказ
        if self.intent_validator.validate_no():
            self.game.restore_prev_state()
            return self.say(texts.skill_level_cancel_text)

        # Пробуем извлечь уровень из слота интента SET_SKILL_LEVEL
        level = self._extract_level_from_intent()

        # Если интент не дал уровень — пробуем распарсить команду напрямую
        if level is None:
            level = self._extract_level_from_command()

        if level is None:
            return self.say(texts.skill_level_invalid_text)

        if self.MIN_LEVEL <= level <= self.MAX_LEVEL:
            self.game.set_skill_level(level)
            self.game.restore_prev_state()
            state_text = texts.state_texts.get(self.game.get_skill_state(), '')
            return self.say(texts.skill_level_changed_text.format(level=level) + '\n' + state_text)
        else:
            return self.say(texts.skill_level_invalid_text)

    def _extract_level_from_intent(self):
        """Извлекает уровень сложности из слота интента SET_SKILL_LEVEL."""
        intents = self.request.get('request', {}).get('nlu', {}).get('intents', {})
        if 'SET_SKILL_LEVEL' in intents:
            level_value = intents['SET_SKILL_LEVEL'].get('slots', {}).get('level', {}).get('value')
            if level_value is not None:
                try:
                    return int(level_value)
                except (ValueError, TypeError):
                    pass
        return None

    def _extract_level_from_command(self):
        """Извлекает уровень сложности из текста команды."""
        command = self.request.get('request', {}).get('command', '')
        try:
            return int(command.strip())
        except (ValueError, TypeError):
            return None
