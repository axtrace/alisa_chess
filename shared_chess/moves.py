"""Распознавание хода с обязательной фильтрацией по легальным ходам позиции."""

import re

import chess

from move_extractor import MoveExtractor

RANKS = {
    'один': '1',
    'два': '2',
    'две': '2',
    'три': '3',
    'четыре': '4',
    'пять': '5',
    'шесть': '6',
    'семь': '7',
    'восемь': '8',
}


def extract_move(board, text):
    raw = text.strip()
    normalized = raw.lower().replace('ё', 'е')
    words = re.findall(r'[\w]+', normalized)
    if any(word in {'не', 'отмена', 'отмени', 'назад'} for word in words):
        raise ValueError('MOVE_NOT_UNDERSTOOD')
    try:
        return board.parse_uci(raw.lower())
    except ValueError:
        pass
    try:
        return board.parse_san(raw)
    except ValueError:
        pass
    uci = re.fullmatch(r'([a-h][1-8])\s*[-–—]?\s*([a-h][1-8])([qrbn]?)', normalized)
    if uci:
        return board.parse_uci(''.join(uci.groups()))
    for word, number in RANKS.items():
        normalized = re.sub(rf'\b{word}\b', number, normalized)
    aliases = {alias: file for file, values in MoveExtractor.file_map.items() for alias in values}
    square_pattern = re.compile(
        r'(?<![\w])(' + '|'.join(sorted(aliases, key=len, reverse=True)) + r')\s*([1-8])(?![\w])'
    )
    squares = [aliases[m[1]] + m[2] for m in square_pattern.finditer(normalized)]
    if len(squares) > 2:
        raise ValueError('MOVE_NOT_UNDERSTOOD')
    # Filter source squares explicitly; the legacy parser primarily matches SAN destinations.
    piece_type = None
    for symbol, names in MoveExtractor.piece_map.items():
        if any(name in words for name in names):
            piece_type = chess.PIECE_SYMBOLS.index(symbol.lower())
    if squares:
        candidates = [
            m
            for m in board.legal_moves
            if chess.square_name(m.to_square) == squares[-1]
            and (len(squares) == 1 or chess.square_name(m.from_square) == squares[0])
            and (piece_type is None or board.piece_type_at(m.from_square) == piece_type)
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError('AMBIGUOUS_MOVE: ' + ', '.join(board.san(m) for m in candidates))
    if 'рокировка' in normalized:
        candidates = [
            m
            for m in board.legal_moves
            if board.is_castling(m)
            and (board.is_queenside_castling(m) if 'длин' in normalized else board.is_kingside_castling(m))
        ]
        if len(candidates) == 1:
            return candidates[0]
    raise ValueError('MOVE_NOT_UNDERSTOOD')
