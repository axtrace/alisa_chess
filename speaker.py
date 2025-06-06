import re
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Speaker(object):
    """
    Class for spelling moves and some texts
    """
    def __init__(self):
        pass

    piece_names = {
        'K': {'ru': 'Король', 'en': 'King'},
        'Q': {'ru': 'Ферзь', 'en': 'Queen'},
        'R': {'ru': 'Ладья', 'en': 'Rock'},
        'N': {'ru': 'Конь', 'en': 'Knight'},
        'B': {'ru': 'Слон', 'en': 'Bishop'},
        'p': {'ru': 'Пешка', 'en': 'Pawn'}
    }

    letters_for_pronunciation = {
        'ru': {'a': 'а', 'b': 'бэ', 'c': 'цэ', 'd': 'дэ', 'e': 'е', 'f': 'эф',
               'g': 'же', 'h': 'аш'}}

    check = {'ru': 'шах.', 'en': 'check.'}

    mate = {'ru': '**мат**.', 'en': '**checkmate**.'}

    checkmate_names = {
        '+': {'ru': 'шах', 'en': 'check'},
        '#': {'ru': '**мат**.', 'en': '**checkmate**'}
    }

    captures_names = {'ru': 'берёт', 'en': 'capture'}

    promotions_names = {'ru': 'превращается в', 'en': 'promotes to'}

    castling_names = {
        '0-0': {'ru': 'Короткая рокировка', 'en': 'Kingside castling'},
        '0-0-0': {'ru': 'Длинная рокировка', 'en': 'Queenside castling'}
    }

    white_black_names = {
        'WHITE': {'ru': 'Белые', 'en': 'White'},
        'BLACK': {'ru': 'Черные', 'en': 'Black'}
    }

    gameover_reasons = {
        '#': {'ru': 'мат', 'en': 'mate'},
        '=': {'ru': 'пат', 'en': 'stalemate'},
        '5': {'ru': 'ничья из-за 5 повторов', 'en': 'fivefold repetition'},
        'insufficient': {'ru': 'ничья из-за недостаточности материала',
                         'en': 'draw due to insufficient material'}
    }

    def _castling_pron_(self, move_san, lang='ru'):
        # returns castling pronunciation in specified language
        res = ''
        castle_index = move_san.replace('O', '0')
        castlings = self.castling_names.get(castle_index, None)
        if castlings is not None:
            res = castlings.get(lang, '')
        return res

    def _file_pron_(self, file, lang='ru'):
        # returns file (column) pronunciation in specified language
        res = file

        letters_set = self.letters_for_pronunciation.get(lang, None)
        if letters_set is not None:
            res = letters_set.get(file, file)
        return res

    def _piece_pron_(self, piece, lang='ru'):
        # return name on lang by piece symbol
        res = ''
        piece_name = self.piece_names.get(piece, None)
        if piece_name is not None:
            res = piece_name.get(lang, '')
        return res

    def _checkmate_pron_(self, cm_type, lang='ru'):
        # returns check or mate pronunciation in specified language
        # todo: stalemate pronunciation
        res = ''
        checkmates = self.checkmate_names.get(cm_type, None)

        if checkmates is not None:
            res = checkmates.get(lang, '')
        return res

    def _capture_pron_(self, lang='ru'):
        # returns capture pronunciation in specified language
        return self.captures_names.get(lang, '')

    def say_move(self, move_san, lang='ru'):
        logger.info(f"say_move received: {move_san}, {lang}")  # Отладочный вывод 
        speak_list = []
        regex_body = r'[a-h]|[1-8]|x|[KQRBN]|[+#]|0-0-0|0-0|O-O-O|O-O'
        move_regex = re.compile(regex_body)
        for sym in re.finditer(move_regex, move_san):
            if '0-0' in sym[0] or 'O-O' in sym[0]:
                # castling
                speak_list.append(self._castling_pron_(sym[0], lang))
            elif 'a' <= sym[0] <= 'h':
                # file
                speak_list.append(self._file_pron_(sym[0], lang))
            elif '1' <= sym[0] <= '8':
                # rank
                speak_list.append(sym[0])
            elif sym[0] in 'KQRBN':
                # piece
                speak_list.append(self._piece_pron_(sym[0], lang))
            elif sym[0] in 'x':
                # capture
                speak_list.append(self._capture_pron_(lang))
            elif sym[0] in '+#':
                # check or mate
                speak_list.append(self._checkmate_pron_(sym[0], lang))
            elif sym[0] in '=':
                # promotion
                speak_list.append(self.promotions_names.get(lang, ''))
        logger.info(f"say_move result: {speak_list}")  # Отладочный вывод
        return ' '.join(speak_list)

    def say_turn(self, who, lang='ru'):
        logger.info(f"say_turn received: {who}, {lang}")  # Отладочный вывод
        res = ''
        if who:  # Проверка на пустую строку или None
            turn_names = self.white_black_names.get(who.upper(), None)
            if turn_names is not None:
                res = turn_names.get(lang, '')
        logger.info(f"say_turn result: {res}")  # Отладочный вывод
        return res

    def say_reason(self, reason, lang='ru'):
        logger.info(f"say_reason received: {reason}, {lang}")  # Отладочный вывод
        res = ''
        reasons = self.gameover_reasons.get(reason, None)
        if reasons is not None:
            res = reasons.get(lang, '')
        logger.info(f"say_reason result: {res}")  # Отладочный вывод
        return res
