import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = PROJECT_ROOT / "data" / "elections.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def initialise_database():
    with sqlite3.connect(DB_PATH) as connection:
        schema = SCHEMA_PATH.read_text()
        connection.executescript(schema)

    print(f"Database created at: {DB_PATH}")


if __name__ == "__main__":
    initialise_database()
