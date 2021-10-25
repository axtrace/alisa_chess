from alice_scripts import say

import texts
from game import Game
from move_extractor import MoveExtractor
from speaker import Speaker
from text_preparer import TextPreparer
from request_parser import RequestParser
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AliceChess(object):
    move_ext = MoveExtractor()
    speaker = Speaker()

    def __init__(self, game: Game, request):
        self.game = game
        # self.request = request
        self.request = RequestParser(request)

    def get_session_state(self):
        return self.game.serialize_state()

    def processRequest(self):
        if bool(self.request.get_command()):
            log.debug("request command is: '%s'", self.request.get_command())
        else:
            log.debug("unknown request: '%s'", self.request)
        if self.request.is_help():
            yield from self.say_help()

        if self.game.get_skill_state() == '':
            # say hi, do you want to play chess? say yes/
            self.game.set_skill_state('SAY_YES')
            yield from self.say_hi()

        # expend confirmation
        while not self.request.is_yes() and self.game.get_skill_state() == 'SAY_YES':
            yield from self.say_not_get_yes()
        if self.game.get_skill_state() == 'SAY_YES':
            self.game.set_skill_state('SAY_CHOOSE_COLOR')

        # say "please choose color"
        if self.game.get_skill_state() == 'SAY_CHOOSE_COLOR':
            self.game.set_skill_state('CHOOSE_COLOR')
            yield from self.say_choose_color()

        # define user color
        if self.game.get_skill_state() == 'CHOOSE_COLOR':
            is_color_defined, user_color = self.move_ext.extract_color(
                self.request)
            while not is_color_defined:
                yield from self.say_not_get_turn()
                is_color_defined, user_color = self.move_ext.extract_color(
                    self.request)
            self.game.set_user_color(user_color)
            self.game.set_skill_state('NOTIFY_STEP')

        game = self.game
        comp_move, prev_turn = '', ''

        # if user plays black, comp does first move
        if self.game.get_user_color() == 'BLACK' and self.game.get_attempts() == 0:
            # user plays black
            prev_turn = game.who()
            comp_move = game.comp_move()
            log.debug("%s %s", prev_turn, comp_move)

        # game circle
        while not game.is_game_over():
            # get user move
            user_move = yield from self.get_move(comp_move, prev_turn,
                                                 text_to_show=game.get_board())
            if user_move == -1:
                # move undo
                yield from self.say_undo_unavailable()

            while not game.is_move_legal(user_move):
                text, text_tts = TextPreparer.say_not_legal_move(user_move,
                                                                 self.speaker.say_move(
                                                                     user_move))
                text += game.get_board()
                log.debug(text)
                user_move = yield from self.get_move(comp_move, prev_turn,
                                                     text,
                                                     text_tts)

            # make user move
            prev_turn = game.who()
            game.user_move(user_move)
            log.debug("%s %s", prev_turn, user_move)

            if not game.is_game_over():
                # check that game is not over and make comp move
                prev_turn = game.who()
                comp_move = game.comp_move()
                log.debug("%s %s", prev_turn, comp_move)

        # form result text
        move_tts = self.speaker.say_move(comp_move)
        reason = game.gameover_reason()
        board_printed = game.get_board()
        text, text_tts = TextPreparer.say_result(comp_move, move_tts, reason,
                                                 self.speaker.say_reason(reason, 'ru'),
                                                 self.speaker.say_turn(prev_turn, 'ru'))

        # say results
        yield from self.say_text(board_printed + text, text_tts, True)
        game.quit()

    def make_comp_move(self):
        if not self.game.is_game_over():
            # check that game is not over and make comp move
            prev_turn = self.game.who()
            comp_move = self.game.comp_move()
            log.debug("%s %s", prev_turn, comp_move)
            return comp_move, prev_turn
        return None

    def prep_text_to_say(self, comp_move, prev_turn, text_to_show, text_to_say,
                         lang='ru'):
        move_to_say = self.speaker.say_move(comp_move, lang)
        prev_turn_tts = self.speaker.say_turn(prev_turn, lang)
        text, text_tts = TextPreparer.say_your_move(comp_move, move_to_say, prev_turn, prev_turn_tts, text_to_show,
                                                    text_to_say)
        return text, text_tts

    def get_move(self, comp_move='', prev_turn='', text_to_show='',
                 text_to_say=''):
        # say the comp move and try extract valid move from user answer

        text, text_tts = self.prep_text_to_say(comp_move, prev_turn, text_to_show, text_to_say, 'ru')
        if self.game.get_skill_state() == 'NOTIFY_STEP':
            self.game.set_skill_state('MAKE_STEP')
            yield from self.say_text(text, text_tts)

        if self.request.is_unmake():
            # user request undo his move
            return -1

        move = self.move_ext.extract_move(self.request)

        while move is None:
            # self.attempts += 1
            not_get, not_get_tts = TextPreparer.say_do_not_get(
                self.request.get_command(),
                self.game.get_attempts())
            log.debug(not_get)
            yield from self.say_text(not_get, not_get_tts)
            move = self.move_ext.extract_move(self.request)

        self.game.set_skill_state('NOTIFY_STEP')
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
        yield from self.say_text(texts.hi_text)

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
        # elif is_request_unmake(request):
        #    yield from say_unmake()
