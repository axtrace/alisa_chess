import re
from request_parser import RequestParser as rp


class MoveExtractor(object):
    """
    Class for extract move from user speech
    """
    file_map = {
        # allowed low register only
        # анна, борис и прочее - из официального фонетического алфавита
        'a': {'a', 'а', 'эй', 'ai', 'alpha', 'анна'},
        'b': {'b', 'bee', 'be', 'б', 'бэ', 'би', 'bravo', 'борис'},
        'c': {'c', 'cee', 'see', 'sea', 'ц', 'цэ', 'си', 'с', 'charlie', 'цапля'},
        'd': {'d', 'dee', 'di', 'de', 'д', 'дэ', 'ди', 'де', 'до', 'да', 'дай', 'delta', 'дмитрий'},
        'e': {'e', 'е', 'ee', 'и', 'echo', 'елена'},
        'f': {'f', 'ef', 'фе', 'фи', 'фэ', 'ф', 'эф', 'foxtrot', 'федор'},
        'g': {'g', 'gee', 'je', 'г', 'гэ', 'ге', 'ж', 'жи', 'же', 'жэ', 'джи', 'golf', 'женя'},
        'h': {'h', 'aitch', 'аш', 'ш', 'эйч', 'x', 'xa', 'xe', 'xэ', 'hotel', 'шура'}
    }

    # rank_map = {
    #     '1': {'1', 'один', 'one'},
    #     '2': {'2', 'two', 'два'},
    #     '3': {'3', 'three', 'три'},
    #     '4': {'4', 'four', 'четыре'},
    #     '5': {'5', 'five', 'пять'},
    #     '6': {'6', 'six', 'шесть'},
    #     '7': {'7', 'seven', 'семь'},
    #     '8': {'8', 'eight', 'восемь'}
    # }

    piece_map = {
        # allowed low register only
        'K': {'king', 'король', 'кинг'},
        'Q': {'queen', 'ферзь', 'королева', 'квин', 'ферз'},
        'R': {'rook', 'ладья', 'ура', 'тура', 'лада'},
        'N': {'knight', 'конь', 'лошадь', 'кон'},
        'B': {'bishop', 'слон', 'офицер', 'сон', 'салон'},
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

    def _get_intents_(self, req):
        """Получает интенты из запроса."""
        if 'request' in req and 'nlu' in req['request'] and 'intents' in req['request']['nlu']:
            return req['request']['nlu']['intents']
        return None

    def _color_by_intents_(self, req):
        """Extract color from intents."""
        intents = self._get_intents_(req)
        if intents:
            if 'WHITE_WORD' in intents:
                return True, 'WHITE'
            elif 'BLACK_WORD' in intents:
                return True, 'BLACK'
        return False, ''

    def extract_color(self, request):
        """Extract color from request."""
        # try to get color from intents
        intent_color = self._color_by_intents_(request)
        if intent_color[0]:
            return intent_color

        # try to get color from tokens
        if 'request' in request and 'command' in request['request']:
            command = request['request']['command'].lower()
            if any(word in command for word in ['белый', 'белые', 'white']):
                return True, 'WHITE'
            elif any(word in command for word in ['черный', 'черные', 'black']):
                return True, 'BLACK'

        return False, ''

    def extract_move(self, request):
        """Извлекает ход из запроса пользователя."""
        # Проверяем рокировку
        if 'request' in request and 'command' in request['request']:
            command = request['request']['command'].lower()
            if 'рокировка' in command or 'castling' in command:
                if 'короткая' in command or 'короткая' in command or 'kingside' in command:
                    return 'O-O'
                if 'длинная' in command or 'длинная' in command or 'queenside' in command:
                    return 'O-O-O'

        # Пробуем извлечь ход из интентов
        move = self._extract_move_from_intents(request)
        if move:
            return move

        # Если интенты не помогли, пробуем извлечь из текста
        move = self._extract_move_from_text(request)
        if move:
            return move

        return None

    def _extract_move_from_intents(self, request):
        """Извлекает ход из интентов."""
        intents = self._get_intents_(request)
        if not intents:
            return None

        # Проверяем интент CHESS_MOVE
        if 'CHESS_MOVE' in intents:
            slots = intents['CHESS_MOVE']['slots']
            piece = self._get_piece_from_intent(slots.get('piece', {}).get('value', ''))
            file_from = slots.get('file_from', {}).get('value', '')
            rank_from = slots.get('rank_from', {}).get('value', '')
            file_to = slots.get('file_to', {}).get('value', '')
            rank_to = slots.get('rank_to', {}).get('value', '')
            
            if file_to and rank_to:  # Минимум нужны координаты назначения
                return ''.join(filter(None, [piece, file_from, rank_from, file_to, rank_to]))

        # Проверяем интент PIECE
        if 'PIECE' in intents:
            piece = self._get_piece_from_intent(intents['PIECE']['slots']['piece']['value'])
            if piece:
                return piece

        return None

    def _get_piece_from_intent(self, piece_value):
        """Преобразует значение фигуры из интента в шахматную нотацию."""
        piece_value = piece_value.lower()
        for piece, values in self.piece_map.items():
            if piece_value in values:
                return piece
        return ''

    def _get_key_(self, request, dict_of_sets):
        # try to get key of dict with has at least one elem in request.lemma
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
            parts = request.split()
            return len(parts) > 0 and lemma == parts[0]
        else:
            # suggest it is request from user
            return request.has_lemmas(lemma)

    def _get_piece_(self, request):
        return self._get_key_(request, self.piece_map)

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

    def _extract_move_from_text(self, request):
        """Извлекает ход из текста запроса."""
        if 'request' not in request or 'command' not in request['request']:
            return None

        command_text = request['request']['command']
        
        # Получаем фигуру
        piece = self._get_piece_(request)
        
        # Получаем клетки (файл и ранг)
        square_rex = re.compile(r'\w+\s*[1-8]', flags=re.IGNORECASE)
        squares = re.findall(square_rex, command_text)
        
        if not squares:
            return None
            
        file_to, rank_to = self._get_square(squares[-1])
        file_from, rank_from = '', ''
        if len(squares) > 1:
            file_from, rank_from = self._get_square(squares[0])
            
        if not (len(file_to) and len(rank_to)):
            return None
            
        # Формируем ход: a5, Bc3, Nf3g5
        return ''.join(filter(None, [piece, file_from, rank_from, file_to, rank_to]))
