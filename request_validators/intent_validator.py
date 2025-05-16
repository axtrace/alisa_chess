from .base_validator import BaseValidator


class IntentValidator(BaseValidator):
    """Класс для валидации интентов."""
    
    def validate_yes(self) -> bool:
        """Проверяет, является ли запрос подтверждением."""
        if self._has_intent('YANDEX.CONFIRM'):
            return True
        confirm_words = ['да', 'yes', 'ок', 'ok', 'давай', 'давайте', 'давай', 'давайте', 'давай', 'давайте']
        return self._has_text(confirm_words)

    def validate_no(self) -> bool:
        """Проверяет, является ли запрос отказом."""
        if self._has_intent('REJECT'):
            return True
        no_words = ['нет', 'no', 'не', 'отмена', 'cancel', 'нет', 'no', 'не', 'отмена', 'cancel']
        return self._has_text(no_words)

    def validate_help(self) -> bool:
        """Проверяет, является ли запрос просьбой о помощи."""
        if self._has_intent('YANDEX.HELP'):
            return True
        help_words = ['помощь', 'help', 'что ты умеешь', 'what can you do', 'помоги', 'помоги', 'помоги', 'помоги', 'помоги', 'помоги']
        return self._has_text(help_words)

    def validate_draw(self) -> bool:
        """Проверяет, является ли запрос предложением ничьей."""
        if self._has_intent('OFFER_DRAW'):
            return True
        draw_words = ['ничья', 'draw', 'предлагаю ничью', 'offer draw', 'ничья', 'draw', 'предлагаю ничью', 'offer draw']
        return self._has_text(draw_words)

    def validate_resign(self) -> bool:
        """Проверяет, является ли запрос предложением сдачи."""
        if self._has_intent('RESIGN'):
            return True
        resign_words = ['сдаюсь', 'resign', 'сдаюсь', 'give up', 'сдаться', 'resign', 'сдаться', 'give up']
        return self._has_text(resign_words)

    def validate_new_game(self) -> bool:
        """Проверяет, является ли запрос предложением новой игры."""
        if self._has_intent('NEW_GAME'):
            return True
        new_game_words = ['новая игра', 'new game', 'начать заново', 'start over', 'новую игру', 'new game', 'новую партию', 'new game', 'новую партию', 'new game']
        return self._has_text(new_game_words)

    def validate_unmake(self) -> bool:
        """Проверяет, является ли запрос отменой хода."""
        if self._has_intent('UNMAKE'):
            return True
        unmake_words = ['отменить ход', 'отмена хода', 'вернуть ход', 'взять ход назад', 'отменить', 'отмена', 'назад', 'back']
        return self._has_text(unmake_words)

    def validate_repeat_last_move(self) -> bool:
        """Проверяет, является ли запрос просьбой повторить последний ход."""
        if self._has_intent('REPEAT_LAST_MOVE'):
            return True
        repeat_words = ['повтори', 'repeat', 'еще раз', 'again', 'повторить', 'repeat', 'еще раз', 'again']
        return self._has_text(repeat_words)
    
    def validate_set_skill_level(self) -> bool:
        """Проверяет, является ли запрос установкой уровня сложности."""
        if self._has_intent('SET_SKILL_LEVEL'):
            return True
        return False
    
    def validate_set_time_level(self) -> bool:
        """Проверяет, является ли запрос установкой времени на ход."""
        if self._has_intent('SET_TIME_LEVEL'):
            return True
        set_time_level_words = ['время', 'time', 'время на ход', 'time per move', 'время', 'time', 'время на ход', 'time per move']
        return self._has_text(set_time_level_words)
    
    def validate_get_skill_level(self) -> bool:
        """Проверяет, является ли запрос получением уровня сложности."""
        if self._has_intent('GET_SKILL_LEVEL'):
            return True
        return False
        
    def validate_show_board(self) -> bool:
        """Проверяет, является ли запрос отображением доски."""
        if self._has_intent('SHOW_BOARD'):
            return True
        show_board_words = ['доска', 'board', 'доску']
        return self._has_text(show_board_words)

    def validate(self) -> bool:
        """Проверяет наличие любого из известных интентов."""
        return any([
            self.validate_yes(),
            self.validate_no(),
            self.validate_help(),
            self.validate_draw(),
            self.validate_resign(),
            self.validate_new_game(),
            self.validate_unmake(),
            self.validate_repeat_last_move(),
            self.validate_set_skill_level(),
            self.validate_set_time_level(),
            self.validate_get_skill_level(),
            self.validate_show_board()
        ]) 