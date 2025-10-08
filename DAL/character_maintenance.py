import sqlite3

import formatter

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
    display_character(name, False)
    return name

# --------------------------------------------------------
# CHARACTER LOADING
# --------------------------------------------------------
def display_character(name, menuFlag):
    """Display a character's current stats and achievements."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Characters WHERE name = ?", (name,))
    char = cursor.fetchone()
    if not char:
        print("Character not found.")
        conn.close()
        return
    conn.close()

    formatter.clear()
    formatter.drawMenuTopper("Your character:")
    print(f"Name: {char[1]}")
    print(f"Credits: {char[2]}")
    print(f"Difficulty: {char[3]}")
    if menuFlag:
        while 1 > 0:
            formatter.drawMenuLine()
            print("1.) Achievements Menu")
            print("2.) Return to Menu")
            menuInput = input(formatter.getInputText("Choice"))
            if menuInput.isnumeric():
                formatter.clear()
                if 0 > int(menuInput) >= 2:
                    input(formatter.getInputText("Wrong Number"))
                match menuInput:
                    case "1":
                       achievement_menu(name)
                    case "2":
                        return
    else :
        input(formatter.getInputText("Enter"))

def achievement_menu(character_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get categories that have achievements for this character
    cursor.execute("""
        SELECT DISTINCT A.category
        FROM Achievements A
        JOIN CharacterAchievements CA ON A.id = CA.achievement_id
        JOIN Characters C ON C.id = CA.character_id
        WHERE C.name = ?
        ORDER BY A.category
    """, (character_name,))
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
    
    cursor.execute("""
        SELECT A.display_name, A.description
        FROM Achievements A
        JOIN CharacterAchievements CA ON A.id = CA.achievement_id
        JOIN Characters C ON C.id = CA.character_id
        WHERE C.name = ? AND A.category = ?
        ORDER BY A.display_name
    """, (character_name, category))
    achievements = cursor.fetchall()
    conn.close()
    
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper(f"{category} Achievements")
        x = 1
        if not achievements:
            print("No achievements in this category yet!")
        else:
            for i, (display_name, description) in enumerate(achievements, 1):
                print(f"{i}.) {display_name}")
                print(f"   {description}")
                formatter.drawMenuLine()
                x += 1
        print(str(x) + ".) Return to Achievement Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            choice = int(menuInput)
            if choice == 1:
                return
            else:
                input(formatter.getInputText("Wrong Number"))

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