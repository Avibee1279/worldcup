import sqlite3
from config import DB_NAME


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(cur, table_name, column_name, column_type):
    try:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    except sqlite3.OperationalError:
        pass


def create_tables_if_needed():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_api_id INTEGER UNIQUE,
        utc_date TEXT,
        status TEXT,
        stage TEXT,
        group_name TEXT,
        home_team_id INTEGER,
        away_team_id INTEGER,
        home_team TEXT,
        away_team TEXT,
        home_crest TEXT,
        away_crest TEXT,
        home_score INTEGER,
        away_score INTEGER
    )
    """)

    # From now on:
    # username = phone number, kept for compatibility with old code/database
    # nickname = name shown on leaderboard
    # phone_number = private, used later for WhatsApp
    # pin = used for login protection
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nickname TEXT,
        phone_number TEXT UNIQUE,
        pin TEXT NOT NULL,
        whatsapp_opt_in INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        match_api_id INTEGER NOT NULL,
        home_pred INTEGER NOT NULL,
        away_pred INTEGER NOT NULL,
        points INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, match_api_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS team_squads (
        team_id INTEGER PRIMARY KEY,
        team_name TEXT,
        crest TEXT,
        squad_json TEXT,
        updated_at TEXT
    )
    """)

    # Match table upgrades
    add_column_if_missing(cur, "matches", "home_team_id", "INTEGER")
    add_column_if_missing(cur, "matches", "away_team_id", "INTEGER")
    add_column_if_missing(cur, "matches", "home_crest", "TEXT")
    add_column_if_missing(cur, "matches", "away_crest", "TEXT")

    # User table upgrades
    add_column_if_missing(cur, "users", "nickname", "TEXT")
    add_column_if_missing(cur, "users", "phone_number", "TEXT")
    add_column_if_missing(cur, "users", "whatsapp_opt_in", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "users", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # Existing old users:
    # use username as phone number and nickname until updated
    cur.execute("""
    UPDATE users
    SET phone_number = username
    WHERE phone_number IS NULL OR phone_number = ''
    """)

    cur.execute("""
    UPDATE users
    SET nickname = username
    WHERE nickname IS NULL OR nickname = ''
    """)

    conn.commit()
    conn.close()


def get_match_count():
    conn = get_db()
    cur = conn.cursor()

    row = cur.execute("SELECT COUNT(*) AS total FROM matches").fetchone()

    conn.close()

    return row["total"] if row else 0
