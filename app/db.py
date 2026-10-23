import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "data.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL DEFAULT 0,
            condition TEXT,
            category TEXT,
            image TEXT,
            status TEXT NOT NULL DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            buyer_name TEXT,
            buyer_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id)
        );
        """
    )
    # migrate older databases that lack buyer_name
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN buyer_name TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def rows_to_list(rows):
    return [dict(r) for r in rows]
