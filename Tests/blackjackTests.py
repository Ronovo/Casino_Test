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

from unittest.mock import patch, mock_open
from unittest import TestCase
from Games import blackjack
import json


class TestBlackjack(TestCase):

    def setUp(self):
        # Mock achievements data
        self.mock_achievements = [
            {"name": "Blackjack_Win", "displayName": "Baby's First Win", "description": "Win a game of Blackjack"},
            {"name": "Blackjack_Lose", "displayName": "The House Always Wins", "description": "Lose a game of Blackjack"},
            {"name": "Blackjack_Draw", "displayName": "What are the chances?", "description": "Draw a game of Blackjack"},
            {"name": "Blackjack_21", "displayName": "21!", "description": "Get a Blackjack"}
        ]

    @patch('Characters.charactermaintenance.saveCharacter')
    @patch('Games.blackjack.input', create=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_PlayerWins_Blackjack(self, mock_file, mocked_input, mock_save):
        #Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11','3']
        mock_file.return_value.read.return_value = json.dumps(self.mock_achievements)
        deck = ['KS','AS','1S','6D','4H']
        testCharacterData = {"Achievements": [], "Name": "TestPlayer"}
        result = blackjack.dealin(deck,testCharacterData)
        self.assertEqual(result, "You win!")

    @patch('Characters.charactermaintenance.saveCharacter')
    @patch('Games.blackjack.input', create=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_DealerWins_Blackjack(self, mock_file, mocked_input, mock_save):
        #3 for Stand (no Ace input needed since no player Aces)
        mocked_input.side_effect = ['3']
        mock_file.return_value.read.return_value = json.dumps(self.mock_achievements)
        deck = ['KS', 'QS', '1S', 'AD']
        testCharacterData = {"Achievements": [], "Name": "TestPlayer"}
        result = blackjack.dealin(deck, testCharacterData)
        self.assertEqual(result, "The house wins!")

    @patch('Characters.charactermaintenance.saveCharacter')
    @patch('Games.blackjack.input', create=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_PlayerWins_DealerOver21(self, mock_file, mocked_input, mock_save):
        #Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11','3']
        mock_file.return_value.read.return_value = json.dumps(self.mock_achievements)
        deck = ['KS','QS','1S','6D','6H']
        testCharacterData = {"Achievements": [], "Name": "TestPlayer"}
        result = blackjack.dealin(deck, testCharacterData)
        self.assertEqual(result, "You win!")

    @patch('Characters.charactermaintenance.saveCharacter')
    @patch('Games.blackjack.input', create=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_Draw21(self, mock_file, mocked_input, mock_save):
        # Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['11', '3']
        mock_file.return_value.read.return_value = json.dumps(self.mock_achievements)
        deck = ['KS', 'AS', '1S', 'AD']
        testCharacterData = {"Achievements": [], "Name": "TestPlayer"}
        result = blackjack.dealin(deck, testCharacterData)
        self.assertEqual(result, "It's a draw!")


