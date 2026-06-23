import sqlite3
from config import DB_NAME, DATABASE_URL


def is_postgres():
    return DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def execute(self, sql, params=None):
        sql = sql.replace("?", "%s")
        self.cursor.execute(sql, params or ())
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def cursor(self):
        return PostgresCursor(self.connection.cursor())

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db():
    if is_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return PostgresConnection(conn)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(cur, table_name, column_name):
    if is_postgres():
        row = cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?
              AND column_name = ?
        """, (table_name, column_name)).fetchone()
        return row is not None

    rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def add_column_if_missing(cur, table_name, column_name, column_type):
    if column_exists(cur, table_name, column_name):
        return

    cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def create_sqlite_tables(cur):
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nickname TEXT,
        phone_number TEXT UNIQUE,
        pin TEXT NOT NULL,
        whatsapp_opt_in INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        match_api_id INTEGER NOT NULL,
        notification_type TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'PREPARED',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT,
        error_message TEXT,
        UNIQUE(user_id, match_api_id, notification_type)
    )
    """)


def create_postgres_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        nickname TEXT,
        phone_number TEXT UNIQUE,
        pin TEXT NOT NULL,
        whatsapp_opt_in INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        match_api_id INTEGER NOT NULL,
        home_pred INTEGER NOT NULL,
        away_pred INTEGER NOT NULL,
        points INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        match_api_id INTEGER NOT NULL,
        notification_type TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'PREPARED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT,
        error_message TEXT,
        UNIQUE(user_id, match_api_id, notification_type)
    )
    """)


def create_tables_if_needed():
    conn = get_db()
    cur = conn.cursor()

    if is_postgres():
        create_postgres_tables(cur)
    else:
        create_sqlite_tables(cur)

    add_column_if_missing(cur, "matches", "home_team_id", "INTEGER")
    add_column_if_missing(cur, "matches", "away_team_id", "INTEGER")
    add_column_if_missing(cur, "matches", "home_crest", "TEXT")
    add_column_if_missing(cur, "matches", "away_crest", "TEXT")

    add_column_if_missing(cur, "users", "nickname", "TEXT")
    add_column_if_missing(cur, "users", "phone_number", "TEXT")
    add_column_if_missing(cur, "users", "whatsapp_opt_in", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "users", "is_admin", "INTEGER DEFAULT 0")

    if is_postgres():
        add_column_if_missing(cur, "users", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    else:
        add_column_if_missing(cur, "users", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

    add_column_if_missing(cur, "notification_logs", "notification_type", "TEXT")
    add_column_if_missing(cur, "notification_logs", "phone_number", "TEXT")
    add_column_if_missing(cur, "notification_logs", "message", "TEXT")
    add_column_if_missing(cur, "notification_logs", "status", "TEXT DEFAULT 'PREPARED'")
    add_column_if_missing(cur, "notification_logs", "sent_at", "TEXT")
    add_column_if_missing(cur, "notification_logs", "error_message", "TEXT")

    cur.execute("""
    UPDATE users
    SET nickname = username
    WHERE nickname IS NULL OR nickname = ''
    """)

    cur.execute("""
    UPDATE users
    SET phone_number = username
    WHERE phone_number IS NULL OR phone_number = ''
    """)

    conn.commit()
    conn.close()



def get_match_count():
    """
    Used by app.py on startup.
    Returns how many matches are already in the database.
    If 0, the app will run the first football-data sync.
    """
    conn = get_db()
    cur = conn.cursor()

    row = cur.execute("SELECT COUNT(*) AS total FROM matches").fetchone()

    conn.close()

    if row is None:
        return 0

    return row["total"]
