"""Embed every article that has no embedding yet. Safe to re-run."""
import time

from google import genai
from google.genai import types

from app.config import get_settings
from app.db import connect
from app.embeddings import embed_text


def main() -> None:
    settings = get_settings()
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=45_000, retry_options=types.HttpRetryOptions(attempts=1)),
    )
    with connect() as conn:
        rows = conn.execute(
            """SELECT a.id, a.title, a.body FROM articles a
               LEFT JOIN article_embeddings e ON e.article_id = a.id
               WHERE e.article_id IS NULL ORDER BY a.id"""
        ).fetchall()
        done = 0
        for row in rows:
            vector, error = embed_text(conn, client, settings, f"{row['title']}. {row['body']}",
                                       kind="article_embedding", article_id=row["id"])
            if vector is None:
                print(f"FAILED {row['title']}: {error}")
                continue
            conn.execute(
                """INSERT INTO article_embeddings (article_id, model, dims, vector)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (article_id) DO NOTHING""",
                (row["id"], settings.embedding_model, len(vector), vector),
            )
            done += 1
            time.sleep(0.7)
        print(f"embedded {done} of {len(rows)} articles")


if __name__ == "__main__":
    main()
