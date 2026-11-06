import os
import time
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Docker 3-Tier Application")

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("POSTGRES_DB", "myapp")
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


@app.on_event("startup")
def startup():
    for attempt in range(10):
        try:
            with get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL
                    )
                """)
            print("Database connected successfully!")
            return
        except psycopg.OperationalError:
            print(f"Waiting for database... {attempt + 1}/10")
            time.sleep(3)

    raise RuntimeError("Could not connect to database")


class Item(BaseModel):
    name: str


@app.get("/api/health")
def health():
    with get_connection() as conn:
        conn.execute("SELECT 1")

    return {
        "status": "ok",
        "database": "connected"
    }


@app.get("/api/items")
def get_items():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name FROM items ORDER BY id"
        ).fetchall()

    return [
        {"id": row[0], "name": row[1]}
        for row in rows
    ]


@app.post("/api/items")
def add_item(item: Item):
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO items (name) VALUES (%s) RETURNING id, name",
            (item.name,)
        ).fetchone()

    return {"id": row[0], "name": row[1]}
