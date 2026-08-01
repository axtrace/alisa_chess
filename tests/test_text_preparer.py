import unittest

from text_preparer import TextPreparer


class TestTextPreparer(unittest.TestCase):
    def test_say_your_move_separates_move_and_board_with_blank_line(self):
        text, _ = TextPreparer().say_your_move(
            comp_move='c5',
            prev_turn='BLACK',
            text_to_show='8 ♜ ♞\n\nВаш ход!',
            text_to_say='. Ваш ход!',
        )

        self.assertEqual(text, 'Черные пошли c5.\n\n8 ♜ ♞\n\nВаш ход!')
