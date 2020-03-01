from flask import Flask
from alice_scripts import Skill, request, say, suggest
import config
import chess.engine
import chess.pgn

app = Flask(__name__)

skill = Skill(__name__)

file_map = {
    # allowed low register only
    'a': {'a', 'а'},
    'b': {'b', 'bee', 'б', 'бэ', 'би'},
    'c': {'c', 'cee', 'ц', 'цэ', 'си'},
    'd': {'ld', 'dee', 'д', 'дэ', 'ди'},
    'e': {'e', 'е', 'и'},
    'f': {'f', 'ef', 'ф', 'эф'},
    'g': {'g', 'gee', 'je', 'ж', 'жи', 'же', 'жэ', 'джи'},
    'h': {'h', 'aitch', 'аш', 'ш', 'эйч'}
}

rank_map = {
    '1': {'1', 'один', 'one'},
    '2': {'2', 'two', 'два'},
    '3': {'3', 'three', 'три'},
    '4': {'4', 'four', 'четыре'},
    '5': {'5', 'five', 'пять'},
    '6': {'6''six', 'шесть'},
    '7': {'7', 'seven', 'семь'},
    '8': {'8', 'eight', 'восемь'}
}

piece_map = {
    # allowed low register only
    'K': {'king', 'король'},
    'Q': {'queen', 'ферзь', 'королева'},
    'R': {'rook', 'ладья', 'тура'},
    'N': {'kNight', 'конь', 'лошадь'},
    'B': {'bishop', 'слон', 'офицер'},
    'p': {'pawn', 'пешка'}
}


def form_move(request):
    piece = get_piece(request)
    file = get_file(request)
    rank = get_rank(request)
    print('[piece, file, rank]:', [piece, file, rank])

    if not (len(file) or len(rank)):
        return None

    return ''.join(filter(None, [piece, file, rank]))


def get_key(request, dict_of_sets):
    # try to get key of dict with has at least one elem in request.lemmas
    for key in dict_of_sets:
        cur_set = dict_of_sets[key]
        for elem in cur_set:
            if request.has_lemmas(elem):
                return key
    return ''


def get_piece(request):
    return get_key(request, piece_map)


def get_file(request):
    return get_key(request, file_map)


def get_rank(request):
    return get_key(request, rank_map)


def get_move(move_to_say):
    # try extract valid move from user answer
    print('get_move started')
    yield say(f'{move_to_say}. Ваш ход!')
    print('get_move 2')

    print(request['request']['original_utterance'])
    move = form_move(request)
    while move is None:
        yield say('Я вас не поняла. Отвечайте в формате "Конь f3"',
                  suggest('Слон', 'Конь', 'Ферзь', 'Ладья'))
        move = form_move(request)

    return str(move)


@skill.script
def run_script():
    yield from say_hi()

    engine_path = "/usr/games/stockfish"
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    board = chess.Board()

    while not board.is_game_over():
        # start the game
        result = engine.play(board, chess.engine.Limit(time=0.1))

        # define the best comp move from engine
        comp_move = board.san(result.move)

        # say it on Russian
        move_to_say = say_move(comp_move, 'ru')
        # yield say(move_to_say)
        print(comp_move)

        # make it on the board
        board.push(result.move)

        print(board)

        # get move from user
        user_move = yield from get_move(move_to_say)

        print(user_move)
        # make it on the board
        board.push_san(user_move)

        print(board)

    yield say(f'Игра окончена!', end_session=True)
    engine.quit()


def get_file_pronunciation(file, lang='ru'):
    # returns file (column) pronunciation in specified language
    res = file
    letters_for_pronunciation = {
        'ru': {'a': 'а', 'b': 'б', 'c': 'ц', 'd': 'д', 'e': 'е', 'g': 'ж',
               'h': 'аш'}}
    letters_set = letters_for_pronunciation.get(lang, None)
    if letters_set is not None:
        res = letters_set.get(file, file)
    return res


def get_square_pronunciation(move_san, lang='ru'):
    # returns column pronunciation in specified language + rank (row) as digit
    file = move_san[-2]
    rank = move_san[-1]
    file_pron = get_file_pronunciation(file, lang)

    return file_pron + rank


def get_piece_name(piece, lang):
    # returns piece name in specified language
    piece_names = {
        'K': {'ru': 'Король', 'en': 'King'},
        'Q': {'ru': 'Ферзь', 'en': 'Queen'},
        'R': {'ru': 'Ладья', 'en': 'Rock'},
        'N': {'ru': 'Конь', 'en': 'Knight'},
        'B': {'ru': 'Слон', 'en': 'Bishop'},
        'p': {'ru': 'Пешка', 'en': 'Pawn'}
    }
    res = ''
    piece_name = piece_names.get(piece, None)
    if piece_name is not None:
        res = piece_name.get(lang, '')
    return res


def get_check_mate_pron(move_san, lang='ru'):
    # returns check or mate pronunciation in specified language
    # todo: stalemate pronunciation
    check = {'ru': 'шах', 'en': 'check'}
    mate = {'ru': 'мат', 'en': 'mate'}

    res = ''

    if '+' in move_san:
        return check.get(lang, '')
    elif '#' in move_san:
        return mate.get(lang, '')
    return res


def get_capture_pron(move_san, lang='ru'):
    captures = {'ru': 'берёт', 'en': 'capture'}
    return captures.get(lang, '')


def say_move(move_san, lang):
    capture_pron = ''
    postfix = ''
    piece = ''

    square_pron = get_square_pronunciation(move_san, lang)

    if len(move_san) > 2:
        piece_candidate = move_san[0]

        if 'a' < piece_candidate < 'h':
            piece = get_piece_name('p', lang)
            piece += ' ' + piece_candidate
        else:
            piece = get_piece_name(piece_candidate, lang)
        capture_pron = get_capture_pron(move_san, lang)

        check_or_mate_pron = get_check_mate_pron(move_san, lang)
        postfix = check_or_mate_pron  # for scaleability in future

    return ' '.join(
        filter(None, [piece, capture_pron, square_pron, postfix])).strip()


def say_hi():
    yield say('Давайте я обыграю вас в шахматы. Готовы?')
    print(request['request']['original_utterance'])


if __name__ == "__main__":
    skill.run(host=config.HOST_IP)
