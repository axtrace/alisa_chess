import unittest

from alice_scripts import Request

from move_extractor import MoveExtractor


class MoveExtractorTest(unittest.TestCase):
    def setUp(self):
        self.move_extractor = MoveExtractor()

    def command(self, command):
        return Request(
            {'request': {'command': command},
             'session': {
                 'session_id': '440518e7-36a2-411a-9a91-e88ce94a8e5c',
                 'user_id': 'beafdead'}
             }
        )

    def extract_move_test(self, command_text, expected_move):
        request = self.command(command_text)
        actual_move = self.move_extractor.extract_move(request)
        if expected_move is None:
            self.assertIsNone(actual_move)
        else:
            self.assertEqual(expected_move, actual_move)

    def test_move_without_piece(self):
        self.extract_move_test('бэ 5', 'b5')

    def test_move_without_space(self):
        self.extract_move_test('e5', 'e5')

    def test_move_with_piece(self):
        self.extract_move_test('Конь эф 3', 'Nf3')

    def test_move_with_from(self):
        self.extract_move_test('Конь эф 3 же 5', 'Nf3g5')

    def test_move_with_2_pieces(self):
        # it returns last found piece by order in setting list
        self.extract_move_test('Слон Конь а 3 цэ 5', 'Na3c5')

    def test_empty_input(self):
        self.extract_move_test('', None)

    def test_two_digits(self):
        self.extract_move_test('1 1', None)

    def test_no_move(self):
        self.extract_move_test('Fill something here', None)

    def test_move_with_excess_text(self):
        self.extract_move_test('Конь гыгыгыгы д 6', 'Nd6')

    def test_move_without_digits(self):
        # it would be good to extract move from here
        self.extract_move_test('Конь гыгыгыгы эф дэ', None)

    def test_move_with_big_digits(self):
        self.extract_move_test('Ладья ф 9', None)

    def test_short_casting(self):
        self.extract_move_test('Короткая рокировка', 'O-O')

    def test_long_casting(self):
        self.extract_move_test('Длинная рокировка', 'O-O-O')

    def test_two_zeros(self):
        self.extract_move_test('Два нуля', 'O-O')
        self.extract_move_test('00', 'O-O')

    def test_three_zeros(self):
        self.extract_move_test('Три нуля', 'O-O-O')
        self.extract_move_test('000', 'O-O-O')


    def test_bishop(self):
        self.extract_move_test('сон да 3', 'Bd3')

    def test_undo(self):
        # undo move is processed outside move_extractor (in alice_chess.AliceChess.get_move)
        self.extract_move_test('отмени ход', None)


if __name__ == '__main__':
    unittest.main()
