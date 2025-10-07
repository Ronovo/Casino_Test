import sqlite3

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
    print("3. 10 Credits - Hard Mode")

    try:
        difficulty = int(input("Enter your difficulty now (1-3):\n"))
    except ValueError:
        difficulty = 2

    difficulty_map = {
        1: ("Easy", 10000),
        2: ("Medium", 1000),
        3: ("Hard", 10)
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
    display_character(name)
    return name

# --------------------------------------------------------
# CHARACTER LOADING
# --------------------------------------------------------
def display_character(name):
    """Display a character's current stats and achievements."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Characters WHERE name = ?", (name,))
    char = cursor.fetchone()
    if not char:
        print("Character not found.")
        conn.close()
        return

    cursor.execute("""
        SELECT A.display_name
        FROM Achievements A
        JOIN CharacterAchievements CA ON A.id = CA.achievement_id
        JOIN Characters C ON C.id = CA.character_id
        WHERE C.name = ?
    """, (name,))
    achievements = [row[0] for row in cursor.fetchall()]
    conn.close()

    print("\nYour character:")
    print(f"Name: {char[1]}")
    print(f"Credits: {char[2]}")
    print(f"Difficulty: {char[4]}")
    print("Achievements: " + (", ".join(achievements) if achievements else "None"))
    print("------------------------------\n")
    input("Press any key to continue to game...")

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
    print("Character Menu")
    print("--------------")
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
            display_character(name)
            return name
        else:
            print("Invalid choice.")
            return load_characters_at_start()