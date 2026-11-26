"""Справка о позиции для обычной и общей голосовой партии."""

import re

import chess

from speaker import Speaker


def position_query(request):
    command = ' '.join(re.findall(r'[а-яёa-z0-9]+', request.get('command', '').lower()))
    intents = request.get('nlu', {}).get('intents', {})
    if 'MY_KNIGHTS' in intents or command in ('где мои кони', 'где стоят мои кони', 'где мой конь'):
        return 'knights'
    if 'DESCRIBE_POSITION' in intents or command in ('назови позицию', 'опиши позицию', 'озвучь расстановку'):
        return 'position'
    return None


_PIECE_NAMES = {
    chess.KING: ('король', 'короли'),
    chess.QUEEN: ('ферзь', 'ферзи'),
    chess.ROOK: ('ладья', 'ладьи'),
    chess.BISHOP: ('слон', 'слоны'),
    chess.KNIGHT: ('конь', 'кони'),
    chess.PAWN: ('пешка', 'пешки'),
}


def position_response(query, board, user_color):
    if user_color not in ('WHITE', 'BLACK'):
        text = 'Сначала начните партию и выберите цвет фигур.'
    elif query == 'knights':
        squares = [chess.square_name(sq) for sq in board.pieces(chess.KNIGHT, user_color == 'WHITE')]
        if squares:
            who = 'Ваш конь' if len(squares) == 1 else 'Ваши кони'
            text = f'{who} на {", ".join(squares)}.'
        else:
            text = 'У вас не осталось коней.'
    else:
        lines = []
        for color, side in ((chess.WHITE, 'Белые'), (chess.BLACK, 'Чёрные')):
            groups = []
            for piece, (single, plural) in _PIECE_NAMES.items():
                squares = [chess.square_name(sq) for sq in board.pieces(piece, color)]
                if squares:
                    name = single if len(squares) == 1 else plural
                    groups.append(f'{name} {", ".join(squares)}')
            lines.append(f'{side}. ' + '. '.join(groups) + '.')
        text = '\n'.join(lines)
    speaker = Speaker()
    tts = re.sub(r'\b[a-h][1-8]\b', lambda m: speaker.say_move(m[0]), text)
    return {'text': text, 'tts': tts, 'end_session': False}
