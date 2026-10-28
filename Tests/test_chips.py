import random
import unittest

from casino.engine.chips import CHIP_VALUES, COLORS, Chips, InsufficientChips
from casino.engine.bets import BetError, read_stake


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


class ReadStakeTests(unittest.TestCase):
    def test_accepts_whole_credits_inside_the_limits(self):
        self.assertEqual(read_stake(5, "Bet", 5, 100), 5)
        self.assertEqual(read_stake(100, "Bet", 5, 100), 100)
        self.assertEqual(read_stake(7, "Bet"), 7)

    def test_limits_are_enforced(self):
        with self.assertRaisesRegex(BetError, "minimum stake is 5 cr"):
            read_stake(4, "Bet", 5, 100)
        with self.assertRaisesRegex(BetError, "maximum stake is 100 cr"):
            read_stake(101, "Bet", 5, 100)

    def test_optional_stakes_may_be_missing_or_zero(self):
        self.assertEqual(read_stake(None, "Trips", optional=True), 0)
        self.assertEqual(read_stake(0, "Trips", optional=True), 0)
        with self.assertRaises(BetError):
            read_stake(0, "Bet")

    def test_rejects_anything_that_is_not_a_positive_whole_number(self):
        for bad in (-5, 2.5, 10.0, "10", True, None, [10], {"amount": 10}, float("nan"), float("inf")):
            with self.subTest(value=bad), self.assertRaises(BetError):
                read_stake(bad, "Bet", 1, 100)
            with self.subTest(value=bad, optional=True):
                if bad is not None:
                    with self.assertRaises(BetError):
                        read_stake(bad, "Bet", 1, 100, optional=True)


if __name__ == "__main__":
    unittest.main()
