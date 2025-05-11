import unittest
from unittest.mock import patch, MagicMock
import chess
from game import Game

class TestGame(unittest.TestCase):
    """Тесты для класса Game."""
    
    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.game = Game()
        self.initial_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_init_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        self.assertEqual(self.game.board.fen(), self.initial_fen)
        self.assertEqual(self.game.skill_state, 'INITIATED')
        self.assertEqual(self.game.skill_level, 1)
        self.assertEqual(self.game.time_level, 0.1)
        self.assertEqual(self.game.user_color, '')
        self.assertFalse(self.game._needs_promotion)


    def test_init_with_game_state(self):
        """Тест инициализации из сохранённого состояния."""
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        game_state = {
            'board_state': fen,
            'skill_state': 'WAITING_MOVE',
            'prev_skill_state': 'WAITING_COLOR',
            'user_color': 'WHITE',
            'skill_level': 2,
            'time_level': 0.3,
            'needs_promotion': False
        }
        
        game = Game(game_state=game_state)
        
        self.assertEqual(game.board.fen(), fen)
        self.assertEqual(game.skill_state, 'WAITING_MOVE')
        self.assertEqual(game.prev_skill_state, 'WAITING_COLOR')
        self.assertEqual(game.user_color, 'WHITE')
        self.assertEqual(game.skill_level, 2)
        self.assertEqual(game.time_level, 0.3)
        self.assertFalse(game._needs_promotion)

    def test_serialize_state(self):
        """Тест сериализации состояния игры."""
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        self.game.board = chess.Board(fen)
        self.game.set_skill_state('WAITING_MOVE')
        self.game.set_user_color('WHITE')

        state = self.game.serialize_state()
        
        self.assertEqual(state['board_state'], fen)
        self.assertEqual(state['skill_state'], 'WAITING_MOVE')
        self.assertEqual(state['prev_skill_state'], 'INITIATED')
        self.assertEqual(state['user_color'], 'WHITE')
        self.assertEqual(state['current_turn'], 'White')
        self.assertEqual(state['skill_level'], 1)
        self.assertEqual(state['time_level'], 0.1)
        self.assertFalse(state['needs_promotion'])

    def test_make_legal_move(self):
        """Тест выполнения допустимого хода."""
        self.assertTrue(self.game.is_valid_move('e4'))
        self.game.user_move('e4')
        
        # Доска должна измениться
        self.assertNotEqual(self.game.board.fen(), self.initial_fen)
        # Пешка должна быть на e4
        self.assertEqual(self.game.board.piece_at(chess.parse_square('e4')).piece_type, chess.PAWN)
        # Теперь ход чёрных
        self.assertEqual(self.game.who(), 'Black')

    def test_make_illegal_move(self):
        """Тест проверки недопустимого хода."""
        # Пешки не могут ходить по диагонали без взятия
        self.assertFalse(self.game.is_valid_move('e3d4'))
        # Конь не может пойти на e4
        self.assertFalse(self.game.is_valid_move('Ne4'))

    def test_is_checkmate(self):
        """Тест на определение мата."""
        # Детский мат
        self.game.board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(self.game.is_checkmate())
        
        # Не мат
        self.game.board = chess.Board()
        self.assertFalse(self.game.is_checkmate())

    def test_is_stalemate(self):
        fen = "7k/8/8/8/8/1q6/8/K7 w - - 0 1"
        game_state = {
            'board_state': fen,
            'skill_state': 'WAITING_MOVE',
            'prev_skill_state': 'WAITING_COLOR',
            'user_color': 'WHITE',
            'skill_level': 2,
            'time_level': 0.3,
            'needs_promotion': False
        }
        
        game = Game(game_state=game_state)

        self.assertFalse(game.is_checkmate())
        self.assertTrue(game.is_stalemate())
        
        # Не пат
        game = Game()
        self.assertFalse(self.game.is_stalemate())

    def test_check_promotion(self):
        """Тест проверки необходимости превращения пешки."""
        # Создаём ситуацию, требующую превращения пешки
        self.game.board = chess.Board("8/P7/8/8/8/8/8/8 w - - 0 1")
        # Делаем ход, который требует превращения
        self.game.board.push(chess.Move.from_uci("a7a8"))
        
        # Должен быть флаг для превращения
        self.assertTrue(self.game.check_promotion())
        self.assertTrue(self.game._needs_promotion)

    def test_promote_pawn(self):
        """Тест превращения пешки."""
        # Создаём ситуацию, требующую превращения пешки
        self.game.board = chess.Board("8/P7/8/8/8/8/8/8 w - - 0 1")
        self.game.board.push(chess.Move.from_uci("a7a8"))
        self.game.check_promotion()
        
        # Превращаем в ферзя
        self.assertTrue(self.game.promote_pawn(chess.QUEEN))
        
        # Проверяем, что на a8 стоит ферзь
        piece = self.game.board.piece_at(chess.parse_square("a8"))
        self.assertEqual(piece.piece_type, chess.QUEEN)
        self.assertEqual(piece.color, chess.WHITE)

    def test_invalid_fen_in_game_state(self):
        """Тест обработки некорректного FEN в состоянии игры."""
        bad_state = {'board_state': 'invalid_fen'}
        with self.assertRaises(ValueError):
            Game(game_state=bad_state)

    def test_missing_board_in_game_state(self):
        """Тест обработки отсутствующей доски в состоянии."""
        # Состояние без board_state должно использовать начальную доску
        state = {
            'skill_state': 'WAITING_MOVE',
            'user_color': 'WHITE'
        }
        game = Game(game_state=state)
        self.assertEqual(game.board.fen(), self.initial_fen)
        self.assertEqual(game.skill_state, 'WAITING_MOVE')
        self.assertEqual(game.user_color, 'WHITE')

    @patch('chess.Board')
    def test_board_exception_handling(self, mock_board):
        """Тест обработки исключений при инициализации доски."""
        mock_board.side_effect = ValueError("Bad FEN")
        
        # При ошибке создания доски из FEN должна использоваться начальная доска
        game_state = {'board_state': 'bad_fen'}
        with self.assertRaises(ValueError):
            Game(game_state=game_state)

    def test_get_board(self):
        """Тест получения текстового представления доски."""
        board_text = self.game.get_board()
        # Проверяем, что возвращается непустая строка с символами фигур
        self.assertIsInstance(board_text, str)
        self.assertGreater(len(board_text), 10)  # должно быть достаточно символов
        self.assertIn('♙', board_text)  # должны быть символы фигур
        self.assertIn('♖', board_text)

    def test_who(self):
        """Тест определения цвета хода"""
        # Изначально ход белых
        # self.assertEqual(self.game.who(), 'White')

        # После хода - ход черных
        self.game.user_move('e4')
        self.assertEqual(self.game.who(), 'Black')

    def test_set_get_user_color(self):
        """Тест установки и получения цвета пользователя."""
        self.assertEqual(self.game.get_user_color(), '')
        self.game.set_user_color('BLACK')
        self.assertEqual(self.game.get_user_color(), 'BLACK')

    def test_set_get_skill_state(self):
        """Тест установки и получения состояния навыка."""
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')
        self.game.set_skill_state('WAITING_MOVE')
        self.assertEqual(self.game.get_skill_state(), 'WAITING_MOVE')
        self.assertEqual(self.game.get_prev_skill_state(), 'INITIATED')

    def test_restore_prev_state(self):
        """Тест восстановления предыдущего состояния."""
        self.game.set_skill_state('WAITING_MOVE')
        self.game.restore_prev_state()
        self.assertEqual(self.game.get_skill_state(), 'INITIATED')
        self.assertEqual(self.game.get_prev_skill_state(), '')

    def test_set_and_serialize_skill_level(self):
        """Тест изменения уровня сложности и сериализации этого значения."""
        self.assertEqual(self.game.skill_level, 1)
        self.game.set_skill_level(5)
        self.assertEqual(self.game.skill_level, 5)
        state = self.game.serialize_state()
        print(f"test_set_and_serialize_skill_level state: {state}")
        self.assertEqual(state['skill_level'], 5)

if __name__ == '__main__':
    unittest.main() 