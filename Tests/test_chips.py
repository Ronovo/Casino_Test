import random
import unittest

from casino.engine.chips import CHIP_VALUES, COLORS, Chips, InsufficientChips


class ChipsTests(unittest.TestCase):
    def test_total_and_lowercase_keys(self):
        chips = Chips({"white": 11, "green": 4})
        self.assertEqual(chips.total, 111)
        self.assertEqual(chips["White"], 11)

    def test_make_change_uses_fewest_chips(self):
        self.assertEqual(Chips.make_change(1234), Chips(Orange=1, Black=2, Green=1, Red=1, White=4))
        self.assertEqual(Chips.make_change(0), Chips())

    def test_subtraction_never_goes_negative(self):
        with self.assertRaises(InsufficientChips):
            Chips(White=1) - Chips(White=2)
        with self.assertRaises(InsufficientChips):
            Chips(White=-1)

    def test_split_off_exact_chips(self):
        taken, left = Chips(White=11, Green=4).split_off(7)
        self.assertEqual(taken, Chips(White=7))
        self.assertEqual(left, Chips(White=4, Green=4))

    def test_split_off_breaks_a_bigger_chip(self):
        taken, left = Chips(Black=1).split_off(26)
        self.assertEqual(taken.total, 26)
        self.assertEqual(left.total, 74)

    def test_split_off_rejects_overdraw(self):
        with self.assertRaises(InsufficientChips):
            Chips(White=3).split_off(4)

    def test_split_off_invariants_on_random_racks(self):
        rng = random.Random(42)
        for _ in range(2000):
            rack = Chips({color: rng.randint(0, 6) for color in COLORS})
            if rack.total == 0:
                continue
            amount = rng.randint(0, rack.total)
            taken, left = rack.split_off(amount)
            self.assertEqual(taken.total, amount)
            self.assertEqual(left.total, rack.total - amount)

    def test_chip_values_are_ascending(self):
        values = [CHIP_VALUES[color] for color in COLORS]
        self.assertEqual(values, sorted(values))

    def test_unknown_colors_and_negative_amounts_are_refused(self):
        with self.assertRaises(KeyError):
            Chips(Gold=1)
        with self.assertRaises(ValueError):
            Chips.make_change(-1)
        with self.assertRaises(ValueError):
            Chips(White=1).split_off(-1)

    def test_repr_lists_the_chips_held(self):
        self.assertEqual(repr(Chips(White=2, Black=1)), "Chips(White=2, Black=1)")


if __name__ == "__main__":
    unittest.main()
