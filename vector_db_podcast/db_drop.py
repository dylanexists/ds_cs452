## This script is used to drop the tables in the database

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

DROP_TABLE = "DROP TABLE IF EXISTS segment, podcast"

with psycopg2.connect(CONNECTION) as conn:
    cursor = conn.cursor()
    cursor.execute(DROP_TABLE)