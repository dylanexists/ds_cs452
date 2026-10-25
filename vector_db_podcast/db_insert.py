## This script is used to insert data into the database
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from utils import fast_pg_insert


DATA_DIR = Path(__file__).parent
DOCUMENT_DIR = DATA_DIR / "documents"
EMBEDDING_DIR = DATA_DIR / "embedding"
SEGMENT_COLUMNS = [
    "id",
    "start_time",
    "end_time",
    "content",
    "embedding",
    "podcast_id",
]
BATCH_SIZE = 5_000

load_dotenv(dotenv_path=DATA_DIR / ".env")


def get_connection_string():
    """Build a psycopg2 connection string from the project's environment."""
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise ValueError("Set POSTGRES_PASSWORD in vector_db_podcast/.env")

    return psycopg2.extensions.make_dsn(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=password,
    )


def _read_embedding_file(filepath):
    """Yield custom_id and vector pairs from one embedding JSONL file."""
    with filepath.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                custom_id = record["custom_id"]
                embedding = record["response"]["body"]["data"][0]["embedding"]
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(
                    f"Invalid embedding record in {filepath.name}, line {line_number}"
                ) from exc

            if len(embedding) != 128:
                raise ValueError(
                    f"Expected 128 values in {filepath.name}, line {line_number}; "
                    f"found {len(embedding)}"
                )

            yield custom_id, embedding


def read_embedding_files():
    """Yield custom_id and vector pairs from all embedding JSONL files."""
    embedding_files = sorted(EMBEDDING_DIR.glob("*.jsonl"))
    if not embedding_files:
        raise FileNotFoundError(f"No embedding JSONL files found in {EMBEDDING_DIR}")

    for filepath in embedding_files:
        yield from _read_embedding_file(filepath)


def _read_document_file(filepath):
    """Yield custom_id and document metadata from one batch request JSONL file."""
    with filepath.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                custom_id = record["custom_id"]
                body = record["body"]
                metadata = body["metadata"]
                document = {
                    "content": body["input"],
                    "podcast_id": metadata["podcast_id"],
                    "title": metadata["title"],
                    "start_time": metadata["start_time"],
                    "end_time": metadata["stop_time"],
                }
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(
                    f"Invalid document record in {filepath.name}, line {line_number}"
                ) from exc

            if not isinstance(document["content"], str):
                raise ValueError(
                    f"Expected document text in {filepath.name}, line {line_number}"
                )

            yield custom_id, document


def read_document_files():
    """Yield custom_id and document metadata from all document JSONL files."""
    document_files = sorted(DOCUMENT_DIR.glob("batch_request_*.jsonl"))
    if not document_files:
        raise FileNotFoundError(f"No document JSONL files found in {DOCUMENT_DIR}")

    for filepath in document_files:
        yield from _read_document_file(filepath)


def _get_file_pairs():
    """Pair each batch request shard with its embedding output shard."""
    document_files = sorted(DOCUMENT_DIR.glob("batch_request_*.jsonl"))
    embedding_files = {path.name: path for path in EMBEDDING_DIR.glob("*.jsonl")}

    if not document_files:
        raise FileNotFoundError(f"No document JSONL files found in {DOCUMENT_DIR}")
    if not embedding_files:
        raise FileNotFoundError(f"No embedding JSONL files found in {EMBEDDING_DIR}")

    pairs = []
    document_names = set()
    for document_path in document_files:
        embedding_name = document_path.name[len("batch_request_"):]
        document_names.add(embedding_name)
        embedding_path = embedding_files.get(embedding_name)
        if embedding_path is None:
            raise FileNotFoundError(
                f"No embedding file matches {document_path.name}"
            )
        pairs.append((document_path, embedding_path))

    extra_embeddings = set(embedding_files) - document_names
    if extra_embeddings:
        raise ValueError(
            f"Embedding files have no matching document files: {sorted(extra_embeddings)}"
        )

    return pairs


def _insert_segment_batch(rows, connection):
    if rows:
        frame = pd.DataFrame.from_records(rows, columns=SEGMENT_COLUMNS)
        fast_pg_insert(frame, connection, "segment", SEGMENT_COLUMNS)


def insert_into_postgres():
    """Insert podcast metadata, then matching transcript and embedding rows."""
    connection = get_connection_string()

    # Gather one row per podcast, using the metadata carried in each document.
    podcasts = {}
    for _, document in read_document_files():
        podcast_id = document["podcast_id"]
        title = document["title"]
        previous_title = podcasts.setdefault(podcast_id, title)
        if previous_title != title:
            raise ValueError(f"Conflicting titles found for podcast {podcast_id}")

    if not podcasts:
        raise ValueError("No podcast records were found in the document files")

    podcast_frame = pd.DataFrame(
        [(podcast_id, title) for podcast_id, title in podcasts.items()],
        columns=["id", "title"],
    )
    fast_pg_insert(podcast_frame, connection, "podcast", ["id", "title"])
    print(f"Inserted {len(podcast_frame):,} podcast rows.")

    # Match embeddings by custom_id within each shard; output line order is not assumed.
    segment_batch = []
    segment_count = 0
    for document_path, embedding_path in _get_file_pairs():
        print(f"Loading segment shard {document_path.name}...")

        embeddings = {}
        for custom_id, embedding in _read_embedding_file(embedding_path):
            if custom_id in embeddings:
                raise ValueError(
                    f"Duplicate embedding custom_id {custom_id} in {embedding_path.name}"
                )
            embeddings[custom_id] = embedding

        for custom_id, document in _read_document_file(document_path):
            if custom_id not in embeddings:
                raise ValueError(
                    f"No embedding found for custom_id {custom_id} in {embedding_path.name}"
                )

            segment_batch.append(
                {
                    "id": custom_id,
                    "start_time": document["start_time"],
                    "end_time": document["end_time"],
                    "content": document["content"],
                    "embedding": embeddings.pop(custom_id),
                    "podcast_id": document["podcast_id"],
                }
            )

            if len(segment_batch) >= BATCH_SIZE:
                _insert_segment_batch(segment_batch, connection)
                segment_count += len(segment_batch)
                segment_batch.clear()

        if embeddings:
            first_unmatched_id = next(iter(embeddings))
            raise ValueError(
                f"{len(embeddings)} embeddings in {embedding_path.name} had no matching "
                f"document; first unmatched custom_id: {first_unmatched_id}"
            )

        _insert_segment_batch(segment_batch, connection)
        segment_count += len(segment_batch)
        segment_batch.clear()
        print(f"Inserted {segment_count:,} segment rows so far.")

    print(f"Finished inserting {segment_count:,} segment rows.")


if __name__ == "__main__":
    insert_into_postgres()
