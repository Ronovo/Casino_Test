import unittest
from Games import poker
from Helpers import deckmaintenance as dm


class MyTestCase(unittest.TestCase):
    def test_general(self):
        hand = []
        currentDeck = dm.restockDeck()

        for x in range(7):
            card = dm.draw(currentDeck)
            hand.append(card)

        print("----------------------------------")
        print("General Test : Deal 7 Random Cards")
        print("----------------------------------")
        result = poker.calculateScoreValue(hand)
        self.assertIsNotNone(result)

    def test_highValueOnly(self):
        print("----------------------------------")
        print("High Value Only Test")
        print("----------------------------------")
        hand = ["AS", "3D", "4C", "8D", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result,1)

    def test_twoKind(self):
        print("----------------------------------")
        print("2 of a Kind Test")
        print("----------------------------------")
        hand = ["AS", "AD", "4C", "8D", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 2)

    def test_twoPair(self):
        print("----------------------------------")
        print("2 Pair Test")
        print("----------------------------------")
        hand = ["AS", "AD", "4C", "4D", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 3)

    def test_threeKind(self):
        print("----------------------------------")
        print("3 of a Kind Test")
        print("----------------------------------")
        hand = ["AS", "AD", "AC", "8D", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 4)

    def test_fourKind(self):
        print("----------------------------------")
        print("4 of a Kind Test")
        print("----------------------------------")
        hand = ["AS", "AD", "AC", "AH", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 8)

    def test_straightLow(self):
        print("----------------------------------")
        print("Straight(Low) Test")
        print("----------------------------------")
        hand = ["AS", "2D", "3C", "4H", "5S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 5)

    def test_straightHigh(self):
        print("----------------------------------")
        print("Straight(High) Test")
        print("----------------------------------")
        hand = ["1S", "JD", "QC", "KH", "AS"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 5)

    def test_flush(self):
        print("----------------------------------")
        print("Flush Test")
        print("----------------------------------")
        hand = ["AS", "2S", "5S", "7S", "1S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 6)

    def test_fullHouse(self):
        print("----------------------------------")
        print("Full House Test")
        print("----------------------------------")
        hand = ["AS", "AD", "AC", "8D", "8S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 7)

    def test_straightFlushLow(self):
        print("----------------------------------")
        print("Straight Flush(Low) Test")
        print("----------------------------------")
        hand = ["AS", "2S", "3S", "4S", "5S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 9)

    def test_straightFlushHigh(self):
        print("----------------------------------")
        print("Straight Flush(High) Test")
        print("----------------------------------")
        hand = ["KS", "QS", "JS", "1S", "9S"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 9)

    def test_royalFlush(self):
        print("----------------------------------")
        print("Royal Flush(Straight Flush High) Test")
        print("----------------------------------")
        hand = ["1S", "JS", "QS", "KS", "AS"]
        result = poker.calculateScoreValue(hand)
        self.assertEqual(result, 10)

if __name__ == '__main__':
    unittest.main()
