"""Run the six required podcast vector similarity queries."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_DIR / ".env")


def get_connection_string():
    """Build a psycopg2 DSN from the project's environment variables."""
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise ValueError(f"Set POSTGRES_PASSWORD in {PROJECT_DIR / '.env'}")

    return psycopg2.extensions.make_dsn(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=password,
    )


# PostgreSQL's pgvector <-> operator returns Euclidean (L2) distance.
SIMILAR_SEGMENTS_SQL = """
SELECT p.title, s.id, s.content, s.start_time, s.end_time,
       s.embedding <-> source.embedding AS distance
FROM segment AS s
JOIN podcast AS p ON p.id = s.podcast_id
CROSS JOIN (SELECT embedding FROM segment WHERE id = %s) AS source
WHERE s.id <> %s
ORDER BY distance ASC, s.id ASC
LIMIT %s;
"""

DISTANT_SEGMENTS_SQL = """
SELECT p.title, s.id, s.content, s.start_time, s.end_time,
       s.embedding <-> source.embedding AS distance
FROM segment AS s
JOIN podcast AS p ON p.id = s.podcast_id
CROSS JOIN (SELECT embedding FROM segment WHERE id = %s) AS source
WHERE s.id <> %s
ORDER BY distance DESC, s.id ASC
LIMIT %s;
"""

SIMILAR_EPISODES_TO_SEGMENT_SQL = """
WITH episode_embeddings AS (
    SELECT podcast_id, AVG(embedding) AS embedding
    FROM segment
    GROUP BY podcast_id
), source AS (
    SELECT podcast_id, embedding
    FROM segment
    WHERE id = %s
)
SELECT p.title,
       episode_embeddings.embedding <-> source.embedding AS distance
FROM episode_embeddings
JOIN podcast AS p ON p.id = episode_embeddings.podcast_id
CROSS JOIN source
WHERE episode_embeddings.podcast_id <> source.podcast_id
ORDER BY distance ASC, p.id ASC
LIMIT %s;
"""

SIMILAR_EPISODES_SQL = """
WITH episode_embeddings AS (
    SELECT podcast_id, AVG(embedding) AS embedding
    FROM segment
    GROUP BY podcast_id
), source AS (
    SELECT embedding
    FROM episode_embeddings
    WHERE podcast_id = %s
)
SELECT p.title,
       episode_embeddings.embedding <-> source.embedding AS distance
FROM episode_embeddings
JOIN podcast AS p ON p.id = episode_embeddings.podcast_id
CROSS JOIN source
WHERE episode_embeddings.podcast_id <> %s
ORDER BY distance ASC, p.id ASC
LIMIT %s;
"""


SEGMENT_QUESTIONS = [
    ("Question 1: five most similar segments to 267:476", "267:476", False),
    ("Question 2: five most dissimilar segments to 267:476", "267:476", True),
    ("Question 3: five most similar segments to 48:511", "48:511", False),
    ("Question 4: five most similar segments to 51:56", "51:56", False),
]
EPISODE_QUERY_SEGMENTS = ["267:476", "48:511", "51:56"]
QUERY_EPISODE_ID = "VeH7qKZr0WI"
RESULT_LIMIT = 5


def query_segments(cursor, segment_id, *, farthest=False, limit=RESULT_LIMIT):
    """Return similar or most distant segments, excluding the source segment.

    Each row is (podcast_title, segment_id, content, start_time, end_time, distance).
    """
    sql = DISTANT_SEGMENTS_SQL if farthest else SIMILAR_SEGMENTS_SQL
    cursor.execute(sql, (segment_id, segment_id, limit))
    return cursor.fetchall()


def query_episodes_for_segment(cursor, segment_id, limit=RESULT_LIMIT):
    """Rank episodes against a segment using each episode's mean embedding.

    The episode containing the query segment is omitted. Each row is
    (podcast_title, distance).
    """
    cursor.execute(SIMILAR_EPISODES_TO_SEGMENT_SQL, (segment_id, limit))
    return cursor.fetchall()


def query_episodes_for_episode(cursor, podcast_id, limit=RESULT_LIMIT):
    """Rank episode mean embeddings, excluding the source episode."""
    cursor.execute(SIMILAR_EPISODES_SQL, (podcast_id, podcast_id, limit))
    return cursor.fetchall()


def _print_rows(title, rows):
    print(f"\n{title}")
    if not rows:
        print("  No results. Check that the source ID exists and the tables are populated.")
        return

    for row in rows:
        if len(row) == 6:
            podcast_title, segment_id, content, start_time, end_time, distance = row
            print(
                f"  title={podcast_title!r} | segment={segment_id} | "
                f"start={start_time} | stop={end_time} | distance={distance:.6f}\n"
                f"    {content}"
            )
        else:
            podcast_title, distance = row
            print(f"  title={podcast_title!r} | distance={distance:.6f}")


def run_queries():
    """Execute and display all six required Canvas questions."""
    connection = psycopg2.connect(get_connection_string())
    try:
        with connection.cursor() as cursor:
            for title, segment_id, farthest in SEGMENT_QUESTIONS:
                rows = query_segments(cursor, segment_id, farthest=farthest)
                _print_rows(title, rows)

            for segment_id in EPISODE_QUERY_SEGMENTS:
                rows = query_episodes_for_segment(cursor, segment_id)
                _print_rows(
                    f"Question 5: five episodes most similar to segment {segment_id}",
                    rows,
                )

            rows = query_episodes_for_episode(cursor, QUERY_EPISODE_ID)
            _print_rows(
                f"Question 6: five episodes most similar to episode {QUERY_EPISODE_ID}",
                rows,
            )
    finally:
        connection.close()


if __name__ == "__main__":
    run_queries()
