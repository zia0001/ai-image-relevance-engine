"""Analyze every article that has no article_metadata yet. Safe to re-run.
Run:  python -m scripts.analyze_articles"""
import json
import time

from google import genai
from google.genai import types

from app.article_analysis import analyze_article
from app.config import get_settings
from app.db import connect


def main() -> None:
    settings = get_settings()
    expected = {a["title"]: a["expected"] for a in json.load(open("data/articles.json", encoding="utf-8"))}
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=45_000, retry_options=types.HttpRetryOptions(attempts=1)),
    )
    print(f"Model: {settings.vision_model}")
    with connect() as conn:
        rows = conn.execute(
            """SELECT a.id, a.title, a.body FROM articles a
               LEFT JOIN article_metadata m ON m.article_id = a.id
               WHERE m.article_id IS NULL ORDER BY a.id"""
        ).fetchall()
        done = 0
        for n, row in enumerate(rows, 1):
            analysis, raw, error = analyze_article(conn, client, settings, row)
            if analysis is None:
                print(f"[{n}/{len(rows)}] FAILED  {row['title'][:45]}: {error}")
            else:
                conn.execute(
                    """INSERT INTO article_metadata (article_id, subject, category, confidence, raw_response)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (article_id) DO NOTHING""",
                    (row["id"], analysis.subject, analysis.category.value, analysis.confidence, raw),
                )
                done += 1
                print(f"[{n}/{len(rows)}] {analysis.category.value:6} conf={analysis.confidence:.2f} "
                      f"{analysis.subject:22} (expected: {expected.get(row['title'], '?')})")
            if n < len(rows):
                time.sleep(settings.seconds_between_calls)
        print(f"\nDone. {done} of {len(rows)} analyzed.")
        for r in conn.execute(
            """SELECT status, count(*) AS calls, round(sum(cost_usd), 5) AS est_cost
               FROM ai_calls WHERE kind = 'article_analysis' GROUP BY status ORDER BY status"""
        ).fetchall():
            print(f"  article_analysis {r['status']:17} calls={r['calls']} est=${r['est_cost']}")


if __name__ == "__main__":
    main()
