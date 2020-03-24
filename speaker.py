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

    castling_names = {
        '0-0': {'ru': 'Короткая рокировка', 'en': 'Kingside castling'},
        '0-0-0': {'ru': 'Длинная рокировка', 'en': 'Queenside castling'}
    }

    def __init__(self):
        pass

    def _castling_pron_(self, move_san, lang='ru'):
        res = ''
        castlings = self.castling_names.get(lang, None)
        if castlings is not None:
            res = castlings.get(move_san, '')
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

    @staticmethod
    def _checkmate_pron_(self, move_san, lang='ru'):
        # returns check or mate pronunciation in specified language
        # todo: stalemate pronunciation
        res = ''
        if '+' in move_san:
            return self.check.get(lang, '')
        elif '#' in move_san:
            return self.mate.get(lang, '')
        return res

    @staticmethod
    def _capture_pron_(move_san, lang='ru'):
        captures = {'ru': 'берёт', 'en': 'capture'}
        if 'x' in move_san:
            return captures.get(lang, '')
        return ''

    def say_move(self, move_san, lang):
        capture_pron = ''
        postfix = ''
        piece = ''

        if '0-0' in move_san:
            # castling detecting
            return self._castling_pron_(move_san)

        square_pron = self._square_pron_(move_san, lang)

        if len(move_san) > 2:
            piece_candidate = move_san[0]

            if 'a' < piece_candidate < 'h':
                piece = self._piece_pron_('p', lang)
                piece += ' ' + piece_candidate
            else:
                piece = self._piece_pron_(piece_candidate, lang)
            capture_pron = self._capture_pron_(move_san, lang)

            check_or_mate_pron = self._checkmate_pron_(move_san, lang)
            postfix = check_or_mate_pron  # for scalability in future

        return ' '.join(
            filter(None, [piece, capture_pron, square_pron, postfix])).strip()
