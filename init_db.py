from psycopg import connect
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")

def init_db():
    with connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    rate INTEGER,
                    glossary_path TEXT,
                    channel TEXT,
                    channel_link TEXT,
                    others TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    client_id INTEGER REFERENCES clients(id),
                    video_link TEXT,
                    rate_per_minute INTEGER,
                    video_length TEXT,
                    price INTEGER,
                    deadline TEXT,
                    settlement_due TEXT,
                    order_number TEXT,
                    delivered BOOLEAN DEFAULT FALSE,
                    revision_requested BOOLEAN DEFAULT FALSE,
                    revision_completed BOOLEAN DEFAULT FALSE,
                    settlement_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS glossaries (
                    id SERIAL PRIMARY KEY,
                    client_id INTEGER REFERENCES clients(id),
                    korean TEXT,
                    english TEXT
                );
            """)

            conn.commit()
            print("✅ 테이블 생성 완료")

if __name__ == "__main__":
    init_db()
