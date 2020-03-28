import unittest
from request_test import RequestTest
from move_extractor import MoveExtractor


class TestMoveExtractor(unittest.TestCase):
    def setUp(self):
        self.move_extractor = MoveExtractor()

    def test_move_without_piece(self):
        request = RequestTest('бэ 5')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'b5')

    def test_move_without_space(self):
        request = RequestTest('e5')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'e5')

    def test_move_with_piece(self):
        request = RequestTest('Конь эф 3')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'Nf3')

    def test_move_with_from(self):
        request = RequestTest('Конь эф 3 же 5')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'Nf3g5')

    def test_move_with_2_pieces(self):
        # it returns first found piece by order in setting list
        request = RequestTest('Слон Конь а 3 цэ 5')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'Na3c5')

    def test_empty_input(self):
        request = RequestTest('')
        move = self.move_extractor.extract_move(request)
        self.assertIsNone(move)

    def test_no_move(self):
        request = RequestTest('Fill something here')
        move = self.move_extractor.extract_move(request)
        self.assertIsNone(move)

    def test_move_with_excess_text(self):
        request = RequestTest('Конь гыгыгыгы д 6')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, 'Nd6')

    def test_move_without_digits(self):
        request = RequestTest('Конь гыгыгыгы эф дэ')
        move = self.move_extractor.extract_move(request)
        self.assertIsNone(move)

    def test_move_with_big_digits(self):
        request = RequestTest('Ладья ф 9')
        move = self.move_extractor.extract_move(request)
        self.assertIsNone(move)

    def test_short_casting(self):
        request = RequestTest('Короткая рокировка')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, '0-0')

    def test_two_zeros(self):
        request = RequestTest('Два нуля')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, '0-0')

    def test_three_zeros(self):
        request = RequestTest('Три нуля')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, '0-0-0')

    def test_long_casting(self):
        request = RequestTest('Длинная рокировка')
        move = self.move_extractor.extract_move(request)
        self.assertEqual(move, '0-0-0')


if __name__ == '__main__':
    unittest.main()
