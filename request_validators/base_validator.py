from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """Базовый класс для валидаторов запросов."""
    
    def __init__(self, request: dict):
        self.request = request

    @abstractmethod
    def validate(self) -> bool:
        """Проверяет запрос на соответствие условиям."""
        pass

    def _has_intent(self, intent_name):
        """Проверяет наличие интента в запросе."""
        if not all(key in self.request.get('request', {}) for key in ['nlu', 'intents']):
            return False
        return intent_name in self.request['request']['nlu']['intents']

    def _has_text(self, list_of_words):
        """Проверяет текстовое совпадение с словами."""
        command = self.request.get('request', {}).get('command', '').lower()
        return any(word.lower() in command for word in list_of_words) 