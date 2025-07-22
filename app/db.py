import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            video_link TEXT,
            rate_per_minute INTEGER,
            video_length TEXT,
            price INTEGER,
            deadline DATETIME,
            delivered BOOLEAN DEFAULT 0,
            revision_requested BOOLEAN DEFAULT 0,
            revision_completed BOOLEAN DEFAULT 0,
            settlement_due DATE,
            settlement_completed BOOLEAN DEFAULT 0,
            order_number TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        """)
    cur.execute("""
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rate INTEGER,
            glossary_path TEXT,
            channel TEXT,
            channel_link TEXT,
            others TEXT
        );
        """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS glossaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            korean TEXT NOT NULL,
            english TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
    """)


    conn.commit()
    conn.close()
