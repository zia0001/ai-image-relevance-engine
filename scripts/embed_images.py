"""Embed the subject + caption of every analyzed image that has no embedding yet.
Run:  python -m scripts.embed_images   (safe to re-run; finished images are skipped)"""
import math
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
    print(f"Embedding model: {settings.embedding_model} ({settings.embedding_dims} dims)")
    with connect() as conn:
        rows = conn.execute(
            """SELECT i.id, i.filename, m.subject, m.caption
               FROM images i
               JOIN image_metadata m ON m.image_id = i.id
               LEFT JOIN image_embeddings e ON e.image_id = i.id
               WHERE e.image_id IS NULL ORDER BY i.id"""
        ).fetchall()
        done = failed = 0
        for n, row in enumerate(rows, 1):
            text = f"{row['subject']}. {row['caption']}"
            vector, error = embed_text(conn, client, settings, text, kind="image_embedding",
                                       image_id=row["id"])
            if vector is None:
                failed += 1
                print(f"[{n}/{len(rows)}] {row['filename']:18} FAILED  {error}")
                continue
            conn.execute(
                """INSERT INTO image_embeddings (image_id, model, dims, vector)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (image_id) DO NOTHING""",
                (row["id"], settings.embedding_model, len(vector), vector),
            )
            done += 1
            norm = math.sqrt(sum(x * x for x in vector))
            if n <= 3 or n % 10 == 0:
                print(f"[{n}/{len(rows)}] {row['filename']:18} dims={len(vector)} length={norm:.4f}")
            time.sleep(0.7)
        print(f"\nDone. {done} embedded, {failed} failed.")
        for r in conn.execute(
            """SELECT status, count(*) AS calls, COALESCE(sum(input_tokens),0) AS tokens,
                      round(sum(cost_usd), 6) AS est_cost
               FROM ai_calls WHERE kind = 'image_embedding' GROUP BY status ORDER BY status"""
        ).fetchall():
            print(f"  image_embedding {r['status']:10} calls={r['calls']} est_tokens={r['tokens']} est=${r['est_cost']}")


if __name__ == "__main__":
    main()
