from alice_scripts_adapter import say

import texts
from game import Game
from move_extractor import MoveExtractor
from speaker import Speaker
from text_preparer import TextPreparer


class AliceChess(object):
    move_ext = MoveExtractor()
    speaker = Speaker()

    def __init__(self, game: Game, request):
        self.game = game
        self.request = request
        print(f"AliceChess initialized with game: {self.game} and request: {self.request}")
    
    
    def get_session_state(self):
        return self.game.serialize_state()

    def processRequest(self):
        print(f"processRequest. Command: {self.request.get('request', {}).get('command')}, state: {self.game.get_skill_state()}")
        
        # Если это первый запрос или состояние INITIATED
        if self.game.get_skill_state() in ['INITIATED', '']:
            self.game.set_skill_state('SAID_HI')
            print(f"State changed from {self.game.get_skill_state()} to SAID_HI")
            yield from self.say_hi()
           
            self.game.set_skill_state('WAITING_CONFIRM')
            print(f"State changed from {self.game.get_skill_state()} to WAITING_CONFIRM")
            

        # Обработка подтверждения
        if self.game.get_skill_state() == 'WAITING_CONFIRM':
            if not self.is_request_yes():
                yield from self.say_not_get_yes()
            self.game.set_skill_state('SAID_CONFIRM')
            print(f"State changed from {self.game.get_skill_state()} to SAID_CONFIRM")
            self.game.set_skill_state('WAITING_COLOR')
            print(f"State changed from {self.game.get_skill_state()} to WAITING_COLOR")
            yield from self.say_choose_color()

        # Обработка выбора цвета
        if self.game.get_skill_state() == 'WAITING_COLOR':
            is_color_defined, user_color = self.move_ext.extract_color(self.request)
            while not is_color_defined:
                yield from self.say_not_get_turn()
                is_color_defined, user_color = self.move_ext.extract_color(self.request)
            self.game.set_user_color(user_color)
            self.game.set_skill_state('SAID_COLOR')
            print(f"State changed from {self.game.get_skill_state()} to SAID_COLOR")
            self.game.set_skill_state('WAITING_MOVE')
            print(f"State changed from {self.game.get_skill_state()} to WAITING_MOVE")

        # Если пользователь играет черными, делаем первый ход
        if self.game.get_user_color() == 'BLACK' and self.game.get_attempts() == 0:
            prev_turn = self.game.who()
            comp_move = self.game.comp_move()
            self.game.set_skill_state('SAID_MOVE')
            print(f"State changed from {self.game.get_skill_state()} to SAID_MOVE")
        # Основной игровой цикл
        while not self.game.is_game_over():
            print(f"CIRCLE while not self.game.is_game_over(). command: {self.request.get('request', {}).get('command')}, state: {self.game.get_skill_state()}")
            
            if self.game.get_skill_state() == 'SAID_MOVE':
                self.game.set_skill_state('WAITING_MOVE')

            user_move = yield from self.get_move(comp_move, prev_turn, text_to_show=self.game.get_board())
            if user_move == -1:
                yield from self.say_undo_unavailable()
                continue

            while not self.game.is_move_legal(user_move):
                text, text_tts = TextPreparer.say_not_legal_move(user_move, self.speaker.say_move(user_move))
                text += self.game.get_board()
                user_move = yield from self.get_move(comp_move, prev_turn, text, text_tts)

            prev_turn = self.game.who()
            self.game.user_move(user_move)
            self.game.set_skill_state('SAID_MOVE')

            if not self.game.is_game_over():
                prev_turn = self.game.who()
                comp_move = self.game.comp_move()

        # Формируем итоговый текст
        move_tts = self.speaker.say_move(comp_move)
        reason = self.game.gameover_reason()
        board_printed = self.game.get_board()
        text, text_tts = TextPreparer.say_result(comp_move, move_tts, reason,
                                               self.speaker.say_reason(reason, 'ru'),
                                               self.speaker.say_turn(prev_turn, 'ru'))

        yield from self.say_text(board_printed + text, text_tts, True)

    def make_comp_move(self):
        if not self.game.is_game_over():
            # check that game is not over and make comp move
            prev_turn = self.game.who()
            comp_move = self.game.comp_move()
            return comp_move, prev_turn
        return None

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say,
                         lang='ru'):
        move_to_say = self.speaker.say_move(comp_move, lang)
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang)
        text, text_tts = TextPreparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show,
                                                    text_to_say)
        return text, text_tts

    def get_move(self, comp_move='', prev_turn='', text_to_show='', text_to_say=''):
        # say the comp move and try extract valid move from user answer
        text, text_tts = self.prep_text_to_say(comp_move, prev_turn, text_to_show, text_to_say, 'ru')
        if self.game.get_skill_state() == 'WAITING_MOVE':
            print(f"Changing state from {self.game.get_skill_state()} to SAID_MOVE")
            self.game.set_skill_state('SAID_MOVE')
            yield from self.say_text(text, text_tts)

        if self.is_request_unmake():
            # user request undo his move
            return -1

        move = self.move_ext.extract_move(self.request)

        while move is None:
            not_get, not_get_tts = TextPreparer.say_do_not_get(
                self.request['request']['command'],
                self.game.get_attempts())
            yield from self.say_text(not_get, not_get_tts)
            move = self.move_ext.extract_move(self.request)

        print(f"Changing state from {self.game.get_skill_state()} to WAITING_MOVE")
        self.game.set_skill_state('WAITING_MOVE')
        return str(move)

    def say_choose_color(self):
        text, text_tts = TextPreparer.say_choose_color()
        yield from self.say_text(text, text_tts)

    def say_undo_unavailable(self):
        text, text_tts = TextPreparer.say_undo_unavailable()
        yield from self.say_text(text, text_tts)

    def say_help(self):
        text, text_tts = TextPreparer.say_help_text()
        yield from self.say_text(text, text_tts)

    def say_hi(self):
        yield from self.say_text(texts.hi_text, texts.hi_text)
        print(f"'ve just SAID HI")

    def say_not_get_yes(self):
        yield from self.say_text(texts.dng_start_text)

    def say_not_get_turn(self):
        yield from self.say_text(texts.not_get_turn_text)

    def say_text(self, text, text_tts='', end_session=False):
        # say text and check answer for help
        tts = text_tts if text_tts else text
        yield say(text, tts=tts, end_session=end_session)
        if self.is_request_help():
            yield from self.say_help()

    def is_request_yes(self):
        """Проверяет, является ли запрос пользователя подтверждением.
        
        Проверяет два условия:
        1. Наличие интента YANDEX.CONFIRM
        2. Текстовое совпадение с подтверждающими словами
        
        Returns:
            bool: True если запрос является подтверждением, False иначе
        """
        if self._has_intent('YANDEX.CONFIRM'):
            return True
        confirm_words = ['да', 'yes', 'ок', 'ok', 'давай']
        return self._has_text(confirm_words)

    def is_request_unmake(self):
        if self._has_intent('YANDEX.UNMAKE'):
            return True
        unmake_words = ['отмена', 'cancel', 'назад', 'back']
        return self._has_text(unmake_words)
    
    def is_request_help(self):
        if self._has_intent('YANDEX.HELP'):
            return True
        help_words = ['помощь', 'help', 'что ты умеешь', 'what can you do']
        return self._has_text(help_words)
  
    def _has_intent(self, intent_name):
        """Проверяет наличие интента в запросе."""
        if not all(key in self.request.get('request', {}) for key in ['nlu', 'intents']):
            return False
        return intent_name in self.request['request']['nlu']['intents']
        
    def _has_text(self, list_of_words):
        """Проверяет текстовое совпадение с словами"""
        command = self.request.get('request', {}).get('command', '').lower()
        return command in list_of_words

