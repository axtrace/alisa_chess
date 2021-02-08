from flask import Flask
from alice_scripts import Skill, request, say, suggest

import config
import texts
from game import Game
from move_extractor import MoveExtractor
from speaker import Speaker
from text_preparer import TextPreparer

app = Flask(__name__)
skill = Skill(__name__)

move_ext = MoveExtractor()
speaker = Speaker()
tp = TextPreparer()

# Globals
attempts = 0


@skill.script
def run_script():
    # main part of program. Enter point
    # attempts -
    global attempts
    attempts += 1

    # say hi, do you want to play chess? say yes/
    yield from say_hi()

    # expend confirmation
    while not is_request_yes(request):
        yield from say_not_get_yes()

    # say "please choose color"
    yield from say_turn()

    # define user color
    # is_color_defined, user_color = color_define(request)
    is_color_defined, user_color = move_ext.extract_color(request)
    while not is_color_defined:
        yield from say_not_get_turn()
        is_color_defined, user_color = move_ext.extract_color(request)

    # start new game
    game = Game()
    comp_move, prev_turn = '', ''

    # if user plays black, comp does first move
    if user_color == 'BLACK':
        # user plays black
        prev_turn = game.who()
        comp_move = game.comp_move()
        print(prev_turn, comp_move)

    # game circle
    while not game.is_game_over():
        # get user move
        user_move = yield from get_move(comp_move, prev_turn,
                                        text_to_show=game.get_board())
        if user_move == -1:
            # отмена хода
            pass
            # continue

        while not game.is_move_legal(user_move):
            text, text_tts = tp.say_not_legal_move(user_move,
                                                   speaker.say_move(user_move))
            text += game.get_board()
            print(text)
            user_move = yield from get_move(comp_move, prev_turn, text,
                                            text_tts)

        # make user move
        prev_turn = game.who()
        game.user_move(user_move)
        print(prev_turn, user_move)

        if not game.is_game_over():
            # check that game is not over and make comp move
            prev_turn = game.who()
            comp_move = game.comp_move()
            print(prev_turn, comp_move)

    # form result text
    move_tts = speaker.say_move(comp_move)
    reason = game.gameover_reason()
    board_printed = game.get_board()
    text, text_tts = tp.say_result(comp_move, move_tts, reason,
                                   speaker.say_reason(reason, 'ru'),
                                   speaker.say_turn(prev_turn, 'ru'))

    # say results
    yield from say_text(board_printed + text, text_tts, True)
    game.quit()


def make_comp_move(game):
    if not game.is_game_over():
        # check that game is not over and make comp move
        prev_turn = game.who()
        comp_move = game.comp_move()
        print(prev_turn, comp_move)
        return comp_move, prev_turn
    return None


def prep_text_to_say(comp_move, prev_turn, text_to_show, text_to_say,
                     lang='ru'):
    move_to_say = speaker.say_move(comp_move, lang)
    prev_turn_tts = speaker.say_turn(prev_turn, lang)
    text, text_tts = tp.say_your_move(comp_move, move_to_say, prev_turn,
                                      prev_turn_tts, text_to_show,
                                      text_to_say)
    return text, text_tts


def get_move(comp_move='', prev_turn='', text_to_show='', text_to_say=''):
    # say the comp move and try extract valid move from user answer
    global attempts

    # move_to_say = speaker.say_move(comp_move, 'ru')
    # prev_turn_tts = speaker.say_turn(prev_turn, 'ru')
    # text, text_tts = tp.say_your_move(comp_move, move_to_say, prev_turn,
    #                                   prev_turn_tts, text_to_show,
    #                                   text_to_say)

    text, text_tts = prep_text_to_say(comp_move, prev_turn, text_to_show,
                                      text_to_say, 'ru')
    yield from say_text(text, text_tts)

    if is_request_unmake(request):
        # user request undo his move
        return -1

    move = move_ext.extract_move(request)

    while move is None:
        attempts += 1
        not_get, not_get_tts = tp.say_do_not_get(request['request']['command'],
                                                 attempts)
        print(not_get)
        yield from say_text(not_get, not_get_tts)
        move = move_ext.extract_move(request)

    return str(move)


def say_turn():
    text, text_tts = tp.say_hi_text('Конь f3', speaker.say_move('Nf3', 'ru'))
    yield from say_text(text, text_tts)


def say_help():
    text, text_tts = tp.say_help_text()
    yield from say_text(text, text_tts)


def say_hi():
    yield from say_text(texts.hi_text)


def say_not_get_yes():
    yield from say_text(texts.dng_start_text)


def say_not_get_turn():
    yield from say_text(texts.not_get_turn_text)


def say_unmake():
    pass


def say_text(text, text_tts='', end_session=False):
    # say text and check answer for help
    tts = text_tts if text_tts else text
    yield say(text, tts=tts, end_session=end_session)
    if is_request_help(request):
        yield from say_help()
    # elif is_request_unmake(request):
    #    yield from say_unmake()


def color_define(req):
    # define user color
    white_lemmas = ['белый', 'белые', 'белых', 'белое', 'white']
    black_lemmas = ['черный', 'черные', 'черных', 'черное', 'black']
    if req.has_lemmas(*white_lemmas):
        return True, 'WHITE'
    elif req.has_lemmas(*black_lemmas):
        return True, 'BLACK'
    return False, ''


def get_intents(req):
    if 'nlu' in req['request']:
        if 'intents' in req['request']['nlu']:
            return req['request']['nlu']['intents']
    return None


def get_entities(req):
    pass


def is_request_yes(req):
    yes_lemmas = ['да', 'давай', 'ага', 'угу', 'yes', 'yeh', 'ok', 'ок',
                  'поехали', 'старт']
    intents = get_intents(req)
    has_lemmas_bool = req.has_lemmas(*yes_lemmas)
    if intents is not None:
        return "YANDEX.CONFIRM" in intents or has_lemmas_bool
    return has_lemmas_bool


def is_request_unmake(req):
    unmake_lemmas = ['отмена', 'отменить', 'отмени', 'отставить', 'unmake',
                     'undo']
    return req.has_lemmas(*unmake_lemmas)


def is_request_help(req):
    # define if user asked help
    help_lemmas = ['помощь', 'умеешь']
    return req.has_lemmas(*help_lemmas)


if __name__ == "__main__":
    cur_host = config.HOST_IP
    port = 5000

    skill.run(host=cur_host, port=5000, ssl_context='adhoc', debug=False)
