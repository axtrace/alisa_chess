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
        'ru': {'a': 'а', 'b': 'б', 'c': 'ц', 'd': 'д', 'e': 'е', 'g': 'ж',
               'h': 'аш'}}

    check = {'ru': 'шах', 'en': 'check'}

    mate = {'ru': 'мат', 'en': 'mate'}

    checkmate_names = {
        '+': {'ru': 'шах', 'en': 'check'},
        '#': {'ru': 'мат', 'en': 'mate'}
    }

    captures_names = {'ru': 'берёт', 'en': 'capture'}

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

    def _square_pron_(self, move_san, lang='ru'):
        # returns column pronunciation in specified language + rank (row) as
        # digit 
        if not move_san:
            return ''

        file = move_san[-2]
        rank = move_san[-1]
        file_pron = self._file_pron_(file, lang)

        return file_pron + rank

    def _piece_pron_(self, piece, lang):
        # returns piece name in specified language
        res = ''
        piece_name = self.piece_names.get(piece, None)
        if piece_name is not None:
            res = piece_name.get(lang, '')
        return res

    def _checkmate_pron_(self, move_san, lang='ru'):
        # returns check or mate pronunciation in specified language
        # todo: stalemate pronunciation
        cm_types = ['#', '+']
        res = ''
        cm_type = ''

        for cm in cm_types:
            if cm in move_san:
                cm_type = cm
                break
        checkmates = self.checkmate_names.get(cm_type, None)

        if checkmates is not None:
            res = checkmates.get(lang, '')
        return res

    def _capture_pron_(self, move_san, lang='ru'):
        if 'x' in move_san:
            return self.captures_names.get(lang, '')
        return ''

    def _say_one_square_move_(self, move_san, lang):
        # todo
        square_pron = self._square_pron_(move_san, lang)

        piece = ''
        if len(move_san) > 2:
            piece_candidate = move_san[0]
            if piece_candidate in self.piece_names.keys():
                piece = self._piece_pron_(piece_candidate, lang)
        return filter(None, [piece, square_pron]).strip()

    def _promoting_pron(self, move_san):
        # e8Q (promoting to queen)
        # todo
        pass

    def say_move(self, move_san, lang):
        capture_pron = ''
        postfix = ''
        piece = ''

        if '0-0' in move_san:
            # castling detected
            return self._castling_pron_(move_san)

        # todo
        
        move_parts = re.split('x', move_san)

        square_moves = []
        for mp in move_parts:
            move_speak = self._say_one_square_move_(mp, lang)
            square_moves.append(move_speak)

        square_pron = self._square_pron_(move_san, lang)

        if len(move_san) > 2:
            piece_candidate = move_san[0]

            if 'a' < piece_candidate < 'h':
                # Пешка а4.
                piece = self._piece_pron_('p', lang)
                piece += ' ' + piece_candidate
            else:
                piece = self._piece_pron_(piece_candidate, lang)

            capture_pron = self._capture_pron_(move_san, lang)

            check_or_mate_pron = self._checkmate_pron_(move_san, lang)
            postfix = check_or_mate_pron

        return ' '.join(
            filter(None, [piece, capture_pron, square_pron, postfix])).strip()
