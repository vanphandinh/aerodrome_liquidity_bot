import sqlite3

DB_PATH = "alerted_positions.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerted_positions (
                key TEXT PRIMARY KEY
            )
        """)

def load_alerted_positions():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT key FROM alerted_positions")
        return set(row[0] for row in cursor.fetchall())


def add_alerted_position(key: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO alerted_positions (key) VALUES (?)", (key,))


def remove_alerted_position(key: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM alerted_positions WHERE key = ?", (key,))


def cleanup_alerted_positions(valid_keys: set):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT key FROM alerted_positions")
        existing_keys = set(row[0] for row in cursor.fetchall())

        keys_to_delete = existing_keys - valid_keys
        for key in keys_to_delete:
            conn.execute("DELETE FROM alerted_positions WHERE key = ?", (key,))
