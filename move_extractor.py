import re


class MoveExtractor(object):
    """
    Class for extract move from user speech
    """
    file_map = {
        # allowed low register only
        # анна, борис и прочее - из официального фонетического алфавита
        'a': {'a', 'а', 'эй', 'ai', 'alpha', 'анна'},
        'b': {'b', 'bee', 'be', 'б', 'бэ', 'би', 'bravo', 'борис'},
        'c': {'c', 'cee', 'see', 'sea', 'ц', 'цэ', 'си', 'с', 'charlie',
              'цапля'},
        'd': {'d', 'dee', 'di', 'de', 'д', 'дэ', 'ди', 'де', 'delta',
              'дмитрий'},
        'e': {'e', 'е', 'ee', 'и', 'echo', 'елена'},
        'f': {'f', 'ef', 'фе', 'фи', 'фэ', 'ф', 'эф', 'foxtrot', 'федор'},
        'g': {'g', 'gee', 'je', 'г', 'гэ', 'ге', 'ж', 'жи', 'же', 'жэ', 'джи',
              'golf', 'женя'},
        'h': {'h', 'aitch', 'аш', 'ш', 'эйч', 'x', 'xa', 'xe', 'xэ', 'hotel',
              'шура'}
    }

    rank_map = {
        '1': {'1', 'один', 'one'},
        '2': {'2', 'two', 'два'},
        '3': {'3', 'three', 'три'},
        '4': {'4', 'four', 'четыре'},
        '5': {'5', 'five', 'пять'},
        '6': {'6', 'six', 'шесть'},
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

    castling_map = {
        'O-O': {'короткая рокировка', 'два нуля', '00', 'kingside castling',
                'castling short', 'short castling', '0-0', 'O-O', 'О-О'},
        'O-O-O': {'длинная рокировка', 'три нуля', '000', 'queenside castling',
                  'castling long', 'long castling', '0-0-0', 'O-O-O', 'О-О-О',
                  'трио'}
    }

    def __init__(self):
        pass

    def extract_move(self, request):
        # extracting move in SAN from user speech

        castling = self._extract_castling(request)
        if castling:
            # castling detected, return it
            return castling

        # get piece from request
        piece = self._get_piece_(request)

        # get square (file and rank) from request
        square_rex = re.compile(r'\w+\s*[1-8]', flags=re.IGNORECASE)
        command_text = request.command
        squares = re.findall(square_rex, command_text)

        if not squares:
            return None

        file_to, rank_to = self._get_square(squares[-1])
        file_from, rank_from = '', ''
        if len(squares) > 1:
            file_from, rank_from = self._get_square(squares[0])

        if not (len(file_to) and len(rank_to)):
            return None

        # a5, Bc3, Nf3g5
        return ''.join(
            filter(None, [piece, file_from, rank_from, file_to, rank_to]))

    def _get_key_(self, request, dict_of_sets):
        # try to get key of dict with has at least one elem in request.lemmas
        for key in dict_of_sets:
            current_dict = dict_of_sets[key]
            for value in current_dict:
                elem_list = value.split()  # if there are few words in value
                has_key = len(elem_list) > 0  # true if list is not empty
                for elem in elem_list:
                    has_key = has_key and self._has_lemma_(request, elem)
                if has_key:
                    return key
        return ''

    @staticmethod
    def _has_lemma_(request, lemma):
        # decorator for str
        if isinstance(request, str):
            # elem looks like 'эф', request looks like 'эф 5'
            return lemma == request.split()[0]
        else:
            # suggest it is request from user
            return request.has_lemmas(lemma)

    def _get_piece_(self, request):
        return self._get_key_(request, self.piece_map)

    def _extract_castling(self, request):
        return self._get_key_(request, self.castling_map)

    def _get_square(self, request):
        return self._get_file_(request), self._get_rank_(request)

    def _get_file_(self, request):
        file_susp = self._get_key_(request, self.file_map)
        if not file_susp:
            # hm, try extract by own way
            if isinstance(request, str):
                # elem looks like 'эф', request looks like 'эф 5'
                text = request
            else:
                # suggest it is request from user
                text = request.command
            text_wo_digits = re.sub(r'[1-8]', '', text)
            file_susp = self._get_key_(text_wo_digits, self.file_map)
        return file_susp

    @staticmethod
    def _get_rank_(request):
        match = re.search(r'[1-8]', request)
        rank = match[0] if match else ''
        return rank
        # return self._get_key_(request, self.rank_map)
