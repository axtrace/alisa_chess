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

    def get_session_state(self):
        return self.game.serialize_state()

    def processRequest(self):
        # Проверяем, есть ли команда в запросе
        if not self.request.get('request', {}).get('command'):
            print(f"Changing state from {self.game.get_skill_state()} to INITIATED")
            self.game.set_skill_state('INITIATED')
            yield from self.say_hi()
            print(f"Changing state from {self.game.get_skill_state()} to SAID_HI")
            self.game.set_skill_state('SAID_HI')
            return

        if self.is_request_help():
            yield from self.say_help()

        if self.game.get_skill_state() == '':
            # say hi, do you want to play chess? say yes/
            print(f"Changing state from {self.game.get_skill_state()} to INITIATED")
            self.game.set_skill_state('INITIATED')
            yield from self.say_hi()
            print(f"Changing state from {self.game.get_skill_state()} to SAID_HI")
            self.game.set_skill_state('SAID_HI')

        # expend confirmation
        if self.game.get_skill_state() in ['INITIATED', 'SAID_HI']:
            if not self.is_request_yes():
                print(f"Changing state from {self.game.get_skill_state()} to WAITING_CONFIRM")
                self.game.set_skill_state('WAITING_CONFIRM')
                yield from self.say_not_get_yes()
            else:
                print(f"Changing state from {self.game.get_skill_state()} to SAID_CONFIRM")
                self.game.set_skill_state('SAID_CONFIRM')
                print(f"Changing state from {self.game.get_skill_state()} to WAITING_COLOR")
                self.game.set_skill_state('WAITING_COLOR')
                yield from self.say_choose_color()

        # define user color
        if self.game.get_skill_state() == 'WAITING_COLOR':
            is_color_defined, user_color = self.move_ext.extract_color(self.request)
            if not is_color_defined:
                yield from self.say_not_get_turn()
            else:
                print(f"Changing state from {self.game.get_skill_state()} to SAID_COLOR")
                self.game.set_user_color(user_color)
                self.game.set_skill_state('SAID_COLOR')
                print(f"Changing state from {self.game.get_skill_state()} to WAITING_MOVE")
                self.game.set_skill_state('WAITING_MOVE')

        game = self.game
        comp_move, prev_turn = '', ''

        # if user plays black, comp does first move
        if self.game.get_user_color() == 'BLACK' and self.game.get_attempts() == 0:
            # user plays black
            prev_turn = game.who()
            comp_move = game.comp_move()
            print(f"Changing state from {self.game.get_skill_state()} to SAID_MOVE (computer)")
            self.game.set_skill_state('SAID_MOVE')

        # game circle
        while not game.is_game_over():
            # get user move
            if self.game.get_skill_state() == 'SAID_MOVE':
                print(f"Changing state from {self.game.get_skill_state()} to WAITING_MOVE")
                self.game.set_skill_state('WAITING_MOVE')

            user_move = yield from self.get_move(comp_move, prev_turn, text_to_show=game.get_board())
            if user_move == -1:
                # move undo
                yield from self.say_undo_unavailable()

            while not game.is_move_legal(user_move):
                text, text_tts = TextPreparer.say_not_legal_move(user_move,
                                                                 self.speaker.say_move(
                                                                     user_move))
                text += game.get_board()
                user_move = yield from self.get_move(comp_move, prev_turn, text, text_tts)

            # make user move
            prev_turn = game.who()
            game.user_move(user_move)
            print(f"Changing state from {self.game.get_skill_state()} to SAID_MOVE (user)")
            self.game.set_skill_state('SAID_MOVE')

            if not game.is_game_over():
                # check that game is not over and make comp move
                prev_turn = game.who()
                comp_move = game.comp_move()

        # form result text
        move_tts = self.speaker.say_move(comp_move)
        reason = game.gameover_reason()
        board_printed = game.get_board()
        text, text_tts = TextPreparer.say_result(comp_move, move_tts, reason,
                                                 self.speaker.say_reason(reason, 'ru'),
                                                 self.speaker.say_turn(prev_turn, 'ru'))

        # say results
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
        # define if user confirm flow
        return 'request' in self.request and 'command' in self.request['request'] and self.request['request']['command'].lower() in ['да', 'yes', 'ок', 'ok']

    def is_request_unmake(self):
        return 'request' in self.request and 'command' in self.request['request'] and self.request['request']['command'].lower() in ['отмена', 'cancel', 'назад', 'back']

    def is_request_help(self):
        # define if user asked help
        return 'request' in self.request and 'command' in self.request['request'] and self.request['request']['command'].lower() in ['помощь', 'help', 'что ты умеешь', 'what can you do']
