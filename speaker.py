import re


class Speaker(object):
    """
    Class for spelling moves
    """
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

    check = {'ru': 'шах', 'en': 'check'}

    mate = {'ru': 'мат', 'en': 'mate'}

    checkmate_names = {
        '+': {'ru': 'шах', 'en': 'check'},
        '#': {'ru': 'мат', 'en': 'mate'}
    }

    captures_names = {'ru': 'берёт', 'en': 'capture'}

    promotions_names = {'ru': 'превращение в', 'en': 'promotion to'}

    castling_names = {

        '0-0': {'ru': 'Короткая рокировка', 'en': 'Kingside castling'},
        '0-0-0': {'ru': 'Длинная рокировка', 'en': 'Queenside castling'}
    }

    def __init__(self):
        pass

    def _castling_pron_(self, move_san, lang='ru'):
        res = ''
        castlings = self.castling_names.get(move_san, None)
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
        return self.captures_names.get(lang, '')

    def say_move(self, move_san, lang):
        speak_list = []
        move_regex = re.compile(r'[a-h]|[1-8]|x|[KQRBN]|[+#]|0-0-0|0-0')
        for sym in re.finditer(move_regex, move_san):
            if '0-0' in sym[0]:
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
        return ' '.join(speak_list)
