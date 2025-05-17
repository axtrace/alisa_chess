import unittest
import chess
from move_extractor import MoveExtractor

class TestFindMatchingMovesRealBoard(unittest.TestCase):
    def setUp(self):
        self.move_ext = MoveExtractor()

    def run_case(self, board_fen, move_structure, expected_moves):
        board = chess.Board(board_fen)
        # Переопределяем san, чтобы вернуть SAN для каждого легального хода
        result = self.move_ext._find_matching_moves(board, move_structure)
        self.assertSetEqual(set(result), set(expected_moves))

    def test_cases(self):
        cases = [
            # 1. Пешечный ход с взятием
            {
                "board": "8/8/8/8/8/p7/1P6/8 w - - 0 1",
                "move_structure": {'piece': '', 'file_from': '', 'rank_from': '', 'file_to': 'a', 'rank_to': '3', 'move': 'a3', 'promotion_piece': ''},
                "matching_moves": ['bxa3']
            },
            # 2. Конь с вертикали c на b3
            {
                "board": "8/8/8/2N5/8/8/3N4/8 w - - 0 1",
                "move_structure": {'piece': 'N', 'file_from': 'c', 'rank_from': '', 'file_to': 'b', 'rank_to': '3', 'move': 'Ncb3', 'promotion_piece': ''},
                "matching_moves": ['Ncb3']
            },
            # 3. Конь на b3 (любой)
            {
                "board": "8/8/8/N1N5/8/8/8/8 w - - 0 1",
                "move_structure": {'piece': 'N', 'file_from': '', 'rank_from': '', 'file_to': 'b', 'rank_to': '3', 'move': 'Nb3', 'promotion_piece': ''},
                "matching_moves": ['Ncb3', 'Nab3']
            },
            # 4. Пешка на e4
            {
                "board": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "move_structure": {'piece': '', 'file_from': '', 'rank_from': '', 'file_to': 'e', 'rank_to': '4', 'move': 'e4', 'promotion_piece': ''},
                "matching_moves": ['e4']
            },
            # 5. Пешка превращается в ферзя на a8
            {
                "board": "8/P7/8/8/8/8/8/8 w - - 0 1",
                "move_structure": {'piece': '', 'file_from': '', 'rank_from': '', 'file_to': 'a', 'rank_to': '8', 'move': 'a8=Q', 'promotion_piece': 'Q'},
                "matching_moves": ['a8=Q']
            },
            # 6. Пешка превращается в коня на b8
            {
                "board": "8/1P6/8/8/8/8/8/8 w - - 0 1",
                "move_structure": {'piece': '', 'file_from': '', 'rank_from': '', 'file_to': 'b', 'rank_to': '8', 'move': 'b8=N', 'promotion_piece': 'N'},
                "matching_moves": ['b8=N']
            },
            # 7. Ладья с вертикали a на e3
            {
                "board": "8/8/8/N1N5/8/R6R/8/8 w - - 0 1",
                "move_structure": {'piece': 'R', 'file_from': 'a', 'rank_from': '', 'file_to': 'e', 'rank_to': '3', 'move': 'Rae3', 'promotion_piece': ''},
                "matching_moves": ['Rae3']
            },
            # 8. Ладья на e3 (любая)
            {
                "board": "8/8/8/N1N5/8/R6R/8/8 w - - 0 1",
                "move_structure": {'piece': 'R', 'file_from': '', 'rank_from': '', 'file_to': 'e', 'rank_to': '3', 'move': 'Re3', 'promotion_piece': ''},
                "matching_moves": ['Rhe3', 'Rae3']
            },
            # 9. Слон на e2
            {
                "board": "8/8/8/8/8/5B2/8/8 w - - 0 1",
                "move_structure": {'piece': 'B', 'file_from': '', 'rank_from': '', 'file_to': 'e', 'rank_to': '2', 'move': 'Be2', 'promotion_piece': ''},
                "matching_moves": ['Be2']
            },
            # 10. Конь на f3
            {
                "board": "8/8/8/8/8/8/8/6N1 w - - 0 1",
                "move_structure": {'piece': 'N', 'file_from': '', 'rank_from': '', 'file_to': 'f', 'rank_to': '3', 'move': 'Nf3', 'promotion_piece': ''},
                "matching_moves": ['Nf3']
            },
        ]
        for i, case in enumerate(cases, 1):
            with self.subTest(case=i):
                self.run_case(case["board"], case["move_structure"], case["matching_moves"])

if __name__ == '__main__':
    unittest.main()