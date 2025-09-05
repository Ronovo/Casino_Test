#Test setup
#1. Build Deck
#2. Do Dealin with card order.
#Card order explained in deck
#deck[0-1] = player hand
#deck[2-3] = dealer hand
#deck[4-x] = cards for player
#deck[x-y] = cards for dealer.
#Example : Player gets Blackjack, Dealer doesn't win
#Deck = [KS,AS,1S,6D,4H]
#Player : KS + AS = 21
#Dealer : 10S + 6D = 16 (Dealer sits on 17)
#Player Stands
#Dealer Hits, 4H = 20
#Player Wins
#Note, if there is an Ace in the stack, there needs to be a value sent every time you deal a card to player.

from unittest import mock
from unittest import TestCase
from Games import blackjack

class TestBlackjack(TestCase):

    @mock.patch('Games.blackjack.input', create=True)
    def test_PlayerWins_Blackjack(self, mocked_input):
        #Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11','3']
        deck = ['KS','AS','1S','6D','4H']
        result = blackjack.dealin(deck)
        self.assertEqual(result, "You win!")

    @mock.patch('Games.blackjack.input', create=True)
    def test_DealerWins_Blackjack(self, mocked_input):
        #3 for Stand
        mocked_input.side_effect = ['3']
        deck = ['KS', 'QS', '1S', 'AD']
        result = blackjack.dealin(deck)
        self.assertEqual(result, "The house wins!")

    @mock.patch('Games.blackjack.input', create=True)
    def test_PlayerWins_DealerOver21(self, mocked_input):
        #Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11','3']
        deck = ['KS','QS','1S','6D','6H']
        result = blackjack.dealin(deck)
        self.assertEqual(result, "You win!")

    @mock.patch('Games.blackjack.input', create=True)
    def test_Draw21(self, mocked_input):
        # Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11', '3']
        deck = ['KS', 'AS', '1S', 'AD']
        result = blackjack.dealin(deck)
        self.assertEqual(result, "It's a draw!")


