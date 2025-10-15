import formatter
from DAL import money_maintenance as mm, character_maintenance as cm

#General Bets Logic:
#"Winnings Total" is the number of winnings you have at the table to cash out.
#"You can manually cash out, or you get cashed out when you leave."
#"Any left on the winnings will not be taken with you.
#0.) Get Character Name and information
#1.) Start with Player Chips.
#2.) Send Player Chips in to select chips menu
#3.) Get selected chip.
#4.) Get Total of selected chips. This is the credits to use.
#5.) Resolve Game
#6.) Apply modifier to total of selected chips. THis is the "Payout Total"
#7.) Add Payout Total to "Winnings Total".



characterData = cm.load_character_by_name("Ronovo")
name = characterData["name"]
print("Pretend you are playing a game of Blackjack.")
print("You are just asked to ante")
input(formatter.getInputText("Enter"))
betChipsTotal = mm.get_bet_chips_total(name)
formatter.clear()
print("Here are your bet chip totals.")
print(betChipsTotal)
cm.remove_player_chips(name, betChipsTotal)
print("Let's pretend you win, so you get a payout of 3:2")
input("Press enter to calculate...")
totalWinnings = betChipsTotal["Total"] * 1.5
totalWinnings = int(totalWinnings)
print("Current winnings is " + str(totalWinnings) + " credits.")
mm.chips_pay_out_menu(name, totalWinnings)

