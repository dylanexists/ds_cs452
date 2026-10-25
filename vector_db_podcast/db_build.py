## This script is used to create the tables in the database

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
if not POSTGRES_PASSWORD:
    raise ValueError("Set POSTGRES_PASSWORD in the project's .env file")

CONNECTION = psycopg2.extensions.make_dsn(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    dbname=os.getenv("POSTGRES_DB", "postgres"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=POSTGRES_PASSWORD,
)

# need to run this to enable vector data type
CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector"

CREATE_PODCAST_TABLE = """
CREATE TABLE IF NOT EXISTS podcast (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL
);
"""
CREATE_SEGMENT_TABLE = """
CREATE TABLE IF NOT EXISTS segment (
    id TEXT PRIMARY KEY,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(128) NOT NULL,
    podcast_id TEXT NOT NULL REFERENCES podcast(id)
);
"""

conn = psycopg2.connect(CONNECTION)
try:
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_EXTENSION)
            cursor.execute(CREATE_PODCAST_TABLE)
            cursor.execute(CREATE_SEGMENT_TABLE)
finally:
    conn.close()


