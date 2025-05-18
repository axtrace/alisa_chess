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
        nlu = self.request.get('request', {}).get('nlu', {})
        intents = nlu.get('intents', {})
        return intent_name in intents

    def _has_text(self, list_of_words):
        """Проверяет текстовое совпадение с словами."""
        command = self.request.get('request', {}).get('command', '').lower()
        return any(word.lower() in command for word in list_of_words) 