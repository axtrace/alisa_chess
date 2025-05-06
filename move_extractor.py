import re


class MoveExtractor:
    """Класс для извлечения ходов из запросов пользователя."""
    
    def __init__(self):
        self.request = None

    def extract_move(self, request):
        """Извлекает ход из запроса пользователя."""
        self.request = request
        command = self._get_command_()
        if not command:
            return None
            
        # Извлекаем ход из команды
        move = self._extract_move_from_text(command)
        return move

    def extract_color(self, request):
        """Извлекает выбранный цвет из запроса пользователя."""
        self.request = request
        command = self._get_command_()
        if not command:
            return False, None
            
        # Проверяем наличие слов, указывающих на цвет
        if any(word in command.lower() for word in ['белыми', 'белый', 'white']):
            return True, 'WHITE'
        elif any(word in command.lower() for word in ['черными', 'черный', 'black']):
            return True, 'BLACK'
            
        return False, None

    def _get_command_(self):
        """Получает команду из запроса."""
        if not self.request:
            return None
        return self.request.get('request', {}).get('command', '')

    def _get_piece_(self, request):
        """Получает выбранную фигуру для превращения пешки."""
        self.request = request
        command = self._get_command_()
        if not command:
            return None
            
        # Проверяем наличие слов, указывающих на фигуру
        command = command.lower()
        if any(word in command for word in ['ферзь', 'queen']):
            return 'Q'
        elif any(word in command for word in ['ладья', 'rook']):
            return 'R'
        elif any(word in command for word in ['слон', 'bishop']):
            return 'B'
        elif any(word in command for word in ['конь', 'knight']):
            return 'N'
            
        return None

    def _extract_move_from_text(self, text):
        """Извлекает ход из текста команды."""
        # Удаляем лишние пробелы и приводим к нижнему регистру
        text = ' '.join(text.lower().split())
        
        # Ищем паттерны ходов
        # e2e4, e2-e4, e2 e4
        if len(text) >= 4:
            # Удаляем все не-буквы и не-цифры
            clean_text = ''.join(c for c in text if c.isalnum())
            if len(clean_text) >= 4:
                # Проверяем, что это похоже на ход (буква-цифра-буква-цифра)
                if (clean_text[0].isalpha() and clean_text[1].isdigit() and
                    clean_text[2].isalpha() and clean_text[3].isdigit()):
                    return clean_text[:4]
        
        return None
