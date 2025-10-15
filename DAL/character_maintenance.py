import sqlite3

import formatter
from DAL import money_maintenance as mm

DB_PATH = "casino.db"

# --------------------------------------------------------
# CHARACTER CREATION
# --------------------------------------------------------
def create_new_character():
    """Create a new character in the database."""
    print("Welcome to the character creator.")
    print("Let's start with your name. Who is going to be betting?")
    name = input("Enter name here:\n")

    print("Now let's start with your difficulty (This ties into achievements)")
    print("Options (Default - Normal):")
    print("1. 10,000 Credits - Easy Mode")
    print("2. 1,000 Credits - Normal Mode")
    print("3. 100 Credits - Hard Mode")
    print("4. 10 Credits - Very Hard Mode")

    try:
        difficulty = int(input("Enter your difficulty now (1-3):\n"))
    except ValueError:
        difficulty = 2

    difficulty_map = {
        1: ("Easy", 10000),
        2: ("Medium", 1000),
        3: ("Hard", 100),
        4: ("Very Hard", 10)
    }

    difficulty_str, start_credits = difficulty_map.get(difficulty, ("Medium", 1000))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Characters (name, credits, difficulty)
        VALUES (?, ?, ?)
    """, (name, start_credits, difficulty_str))
    conn.commit()
    conn.close()

    print(f"Character '{name}' created with {start_credits} credits ({difficulty_str}).")

    chips = mm.getStartingChips(name, difficulty_str, start_credits)
    insertStartingChips(name,chips)
    display_character(name, False)
    return name

# --------------------------------------------------------
# CHARACTER LOADING
# --------------------------------------------------------
def display_character(name, menuFlag):
    #Get the total amount from chips for the total net worth
    characterData = load_character_by_name(name)
    chipsToTotal = mm.get_chips_by_character_id(characterData["id"])
    chipTotal = mm.get_chips_total(chipsToTotal)
    total = chipTotal["Total"]

    formatter.clear()
    formatter.drawMenuTopper("Your character:")
    print(f"Name: {characterData['name']}")
    print(f"Total Net Worth: {total}")
    print(f"Difficulty: {characterData['difficulty']}")
    if menuFlag:
        while 1 > 0:
            formatter.drawMenuLine()
            print("1.) Achievements Menu")
            print("2.) Chips Information")
            print("3.) Return to Menu")
            menuInput = input(formatter.getInputText("Choice"))
            if menuInput.isnumeric():
                formatter.clear()
                if 0 > int(menuInput) >= 3:
                    input(formatter.getInputText("Wrong Number"))
                match menuInput:
                    case "1":
                       achievement_menu(name)
                    case "2":
                        mm.chipsMenu(name)
                    case "3":
                        return
    else :
        input(formatter.getInputText("Enter"))

def achievement_menu(character_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all categories from achievements table
    cursor.execute("""
        SELECT DISTINCT category
        FROM Achievements
        ORDER BY category
    """)
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not categories:
        formatter.clear()
        formatter.drawMenuTopper("Achievements")
        print("No achievements unlocked yet!")
        input(formatter.getInputText("Enter"))
        return
    
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Achievements")
        
        # Display category options
        for i, category in enumerate(categories, 1):
            print(f"{i}.) {category}")
        
        # Return option
        return_option = len(categories) + 1
        print(f"{return_option}.) Return to Menu")
        
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            choice = int(menuInput)
            if 1 <= choice <= len(categories):
                # Show achievements in selected category
                show_category_achievements(character_name, categories[choice - 1])
            elif choice == return_option:
                return
            else:
                input(formatter.getInputText("Wrong Number"))

def show_category_achievements(character_name, category):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all achievements in this category
    cursor.execute("""
        SELECT id, display_name, description
        FROM Achievements
        WHERE category = ?
        ORDER BY id
    """, (category,))
    all_achievements = cursor.fetchall()

    # Get character's unlocked achievements in this category
    cursor.execute("""
        SELECT A.id
        FROM Achievements A
        JOIN CharacterAchievements CA ON A.id = CA.achievement_id
        JOIN Characters C ON C.id = CA.character_id
        WHERE C.name = ? AND A.category = ?
    """, (character_name, category))
    unlocked_ids = {row[0] for row in cursor.fetchall()}

    conn.close()

    # Prepare achievements list with hidden/unlocked status
    achievements = []
    for achievement_id, display_name, description in all_achievements:
        if achievement_id in unlocked_ids:
            achievements.append((display_name, description))
        else:
            achievements.append(("Hidden Achievement", "Hidden Achievement"))
    
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper(f"{category} Achievements")
        if not achievements:
            print("No achievements found in this category!")
        else:
            for i, (display_name, description) in enumerate(achievements, 1):
                print(f"{i}.) {display_name}")
                print(f"   {description}")
                formatter.drawMenuLine()
        input(formatter.getInputText("Enter"))
        return

def load_all_characters():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Characters ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names

def load_character_by_name(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Characters WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    keys = [desc[0] for desc in cursor.description]
    return dict(zip(keys, row))

# --------------------------------------------------------
# CHARACTER MENU
# --------------------------------------------------------
def load_characters_at_start():
    names = load_all_characters()
    formatter.drawMenuTopper("Character Menu")
    n = 1
    for option in names:
        print(f"{n}.) {option}")
        n += 1
    print(f"{n}.) Create New Character")
    print(f"{n + 1}.) Quit\n")

    answer = input("Please choose an option:\n")
    try:
        choice = int(answer)
    except ValueError:
        print("Invalid input.")
        return load_characters_at_start()

    if choice == n:
        return create_new_character()
    elif choice == (n + 1):
        quit()
    else:
        index = choice - 1
        if 0 <= index < len(names):
            name = names[index]
            display_character(name, False)
            return name
        else:
            print("Invalid choice.")
            return load_characters_at_start()

# --------------------------------------------------------
# Chips
# --------------------------------------------------------
def insertStartingChips(name,chips):
    """Insert starting chips for a character into PlayerChips table."""
    # Get character_id for the given name
    characterData = load_character_by_name(name)
    if not characterData:
        print(f"Character '{name}' not found.")
        return

    character_id = characterData['id']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert chips data into PlayerChips table
    # Map chip colors to their respective column names
    cursor.execute("""
        INSERT INTO PlayerChips (character_id, white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        character_id,
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))

    conn.commit()
    conn.close()
    print(f"Starting chips assigned to character '{name}'.")

def update_player_chips(chips, character_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert chips data into PlayerChips table
    # Map chip colors to their respective column names
    cursor.execute("""
                UPDATE PlayerChips
                SET white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                WHERE character_id = ?
            """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0),
        character_id,
    ))

    chipTotal = mm.get_chips_total(chips)
    # Update Character Credits
    cursor.execute("""
                    UPDATE Character
                    SET credits = ?
                    WHERE character_id = ?
                """, (
        chipTotal["Total"],
        character_id,
    ))

    conn.commit()
    conn.close()

def update_player_chips_add(name, chips):
    # Get character_id for the given name
    characterData = load_character_by_name(name)
    if not characterData:
        print(f"Character '{name}' not found.")
        return

    character_id = characterData['id']
    characterChips = mm.get_chips_by_character_id(character_id)
    for x in chips:
        characterChips[x] += chips[x]
    update_player_chips(characterChips, character_id)


def remove_player_chips(name, chips):
    # Get character_id for the given name
    characterData = load_character_by_name(name)
    if not characterData:
        print(f"Character '{name}' not found.")
        return

    character_id = characterData['id']
    characterChips = mm.get_chips_by_character_id(character_id)
    for color in ['White', 'Red', 'Green', 'Black', 'Purple', 'Orange']:
        if color in characterChips and color in chips:
            characterChips[color] -= chips[color]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert chips data into PlayerChips table
    # Map chip colors to their respective column names
    cursor.execute("""
            UPDATE PlayerChips
            SET white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
            WHERE character_id = ?
        """, (
        characterChips.get('White', 0),
        characterChips.get('Red', 0),
        characterChips.get('Green', 0),
        characterChips.get('Black', 0),
        characterChips.get('Purple', 0),
        characterChips.get('Orange', 0),
        character_id,
    ))

    conn.commit()
    conn.close()

