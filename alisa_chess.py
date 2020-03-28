import sys
import re
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
    move = move_ext.extract_move(request)
    attempts = 0
    while move is None:
        attempts += 1
        print(request['request']['command'])
        not_get = texts.not_get_move.format(request['request']['command'])
        not_get_tts = not_get
        if attempts % 3 == 1:
            not_get += texts.names_for_files.format('', '', '', '', '', '', '')
            not_get_tts += texts.names_for_files.format('sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>',
                                                        'sil <[60]>')
        yield say(not_get, tts=not_get_tts)
        move = move_ext.extract_move(request)

    return str(move)


@skill.script
def run_script():
    yield from say_hi()
    while not request.has_lemmas('да', 'давай', 'ага', 'угу', 'yes', 'yeh'):
        yield from say_do_not_get()

    yield from say_turn()

    white_lemmas = ['белый', 'белые', 'белых', 'белое', 'white']
    black_lemmas = ['черный', 'черные', 'черных', 'черное', 'black']
    white_and_black_lemmas = white_lemmas + black_lemmas
    while not request.has_lemmas(*white_and_black_lemmas):
        print(request['request']['command'])
        print(request.lemmas)
        yield from say_do_not_get_turn()

    game = Game()
    comp_move = ''
    prev_turn = ''

    if request.has_lemmas(*black_lemmas):
        # user plays black
        prev_turn = game.who()
        comp_move = game.comp_move()
        print(prev_turn, comp_move)

    # get user move
    while not game.is_game_over():
        user_move = yield from get_move(comp_move, prev_turn)
        while not game.is_move_legal(user_move):
            text = texts.not_legal_move.format(user_move)
            tts = texts.not_legal_move.format(speaker.say_move(user_move))
            user_move = yield from get_move(comp_move, prev_turn, text, tts)

        # make user move
        prev_turn = game.who()
        game.user_move(user_move)
        print(prev_turn, user_move)

        # comp make move
        prev_turn = game.who()
        comp_move = game.comp_move()
        print(prev_turn, comp_move)

    move_tts = speaker.say_move(comp_move)
    winner = ''
    reason = game.gameover_reason()
    if reason == '#':
        winner += ' Победили '
        winner += speaker.say_turn(prev_turn, 'ru')
    result = speaker.say_reason(reason, 'ru')

    text = f'{comp_move}. Игра окончена!  Результат: {result}.{winner}'
    text_tts = f'{move_tts}. Игра окончена! sil <[70]> Результат: {result}.{winner}'
    yield say(text, tts=text_tts, end_session=True)
    game.quit()


def say_turn():
    text = texts.hi_turn_text.format('', '', '', '', '',
                                     'Конь f3') + texts.choose_turn_text
    move_to_say = speaker.say_move('Nf3', 'ru')
    tts_text = texts.hi_turn_text.format('sil <[70]>', 'sil <[60]>',
                                         'sil <[60]>', 'sil <[60]>',
                                         'sil <[60]>',
                                         move_to_say) + texts.choose_turn_text
    yield say(text, tts=tts_text)


def say_do_not_get():
    yield say(texts.dng_start_text)


def say_do_not_get_turn():
    yield say(texts.not_get_turn_text)


def say_hi():
    yield say(texts.hi_text)


if __name__ == "__main__":
    cur_host = config.HOST_IP
    port = 5000

    skill.run(host=cur_host, port=5000,
              ssl_context=(config.ssl_cert, config.ssl_priv), debug=False)
