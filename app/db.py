from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_connection():
    return engine.connect()

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                rate INTEGER,
                glossary_path TEXT,
                channel TEXT,
                channel_link TEXT,
                others TEXT
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                video_link TEXT,
                rate_per_minute INTEGER,
                video_length TEXT,
                price INTEGER,
                deadline TIMESTAMP,
                delivered BOOLEAN DEFAULT FALSE,
                revision_requested BOOLEAN DEFAULT FALSE,
                revision_completed BOOLEAN DEFAULT FALSE,
                settlement_due DATE,
                settlement_completed BOOLEAN DEFAULT FALSE,
                order_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS glossaries (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                korean TEXT NOT NULL,
                english TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
