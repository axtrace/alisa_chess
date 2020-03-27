import sys
from flask import Flask
from alice_scripts import Skill, request, say, suggest
import chess.engine
import chess.pgn

import config
import texts
from game import Game
from move_extractor import MoveExtractor
from speaker import Speaker

app = Flask(__name__)
skill = Skill(__name__)

move_ext = MoveExtractor()
speaker = Speaker()


def get_move(comp_move='', prev_turn='', text_to_show='',
             text_to_say=''):
    # say the robot move and try extract valid move from user answer
    text = text_to_show + '. '
    tts = text_to_say + '. '
    if prev_turn:
        turn_to_say = speaker.say_turn(prev_turn)
        tts += f'{turn_to_say} пошли '
        text += f'{turn_to_say} пошли '
    if comp_move:
        move_to_say = speaker.say_move(comp_move, 'ru')
        tts += f'{move_to_say}. '
        text += f'{comp_move}. '
    tts += 'Ваш ход!'
    text += 'Ваш ход!'

    yield say(text, tts=tts)
    move = MoveExtractor.extract_move(request)

    while move is None:
        not_get = texts.not_get_move.format(request['request']['command'])
        yield say(not_get)
        move = MoveExtractor.extract_move(request)

    return str(move)


@skill.script
def run_script():
    yield from say_hi()
    while not request.has_lemmas('да', 'давай', 'ага', 'угу', 'yes', 'yeh'):
        yield from say_do_not_get

    yield from say_turn()
    while not request.has_lemmas('белый', 'белые', 'white', 'черный', 'черные',
                                 'black'):
        yield from say_do_not_get_turn

    game = Game()
    move_to_say = ''
    comp_move = ''
    prev_turn = ''

    if request.has_lemmas('черный', 'black'):
        # user plays black
        prev_turn = game.who()
        comp_move = game.comp_move()

    # get user move
    while not game.is_game_over():
        user_move = yield from get_move(comp_move, prev_turn)
        while not game.is_move_legal(user_move):
            text = texts.not_legal_move.format(user_move)
            tts = texts.not_legal_move.format(speaker.say_move(user_move))
            user_move = yield from get_move(comp_move, prev_turn, text, tts)

        print(user_move)
        # make user move
        game.user_move(user_move)

        # comp make move
        prev_turn = game.who()
        comp_move = game.comp_move()

    yield say(f'Игра окончена! ', end_session=True)
    game.quit()


def say_turn():
    text = texts.hi_turn_text.format('Конь f3') + texts.choose_turn_text
    tts_text = texts.hi_turn_text.format(
        speaker.say_move('Nf3', 'ru')) + texts.choose_turn_text
    yield say(text, tts=tts_text)


def say_do_not_get():
    yield say(texts.dng_start_text)


def say_do_not_get_turn():
    yield say(texts.not_get_turn_text)


def say_hi():
    yield say(texts.hi_text)


if __name__ == "__main__":
    if 'win' in str(sys.platform):
        # it seems this is my win home comp
        cur_host = config.TEST_IP
    else:
        # lets sugget it is production ruvds server
        cur_host = config.HOST_IP
    skill.run(host=cur_host)
