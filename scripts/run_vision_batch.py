"""Run the vision job on every pending image.
Try a few first:  python -m scripts.run_vision_batch --limit 5
Then the rest:    python -m scripts.run_vision_batch"""
import argparse

from google import genai
from google.genai import types

from app.config import get_settings
from app.db import connect
from app.vision import run_vision_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only process this many images")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is missing from .env")
    print(f"Model: {settings.vision_model}")
    client = genai.Client(
        api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=45_000, retry_options=types.HttpRetryOptions(attempts=1))
    )

    with connect() as conn:
        summary = run_vision_batch(conn, client, settings, limit=args.limit)
        print(
            f"\nDone. {summary['done']} analyzed ({summary['flagged']} flagged for review), "
            f"{summary['failed']} failed, {summary['skipped']} skipped."
        )
        print("\nAI calls so far (from ai_calls):")
        rows = conn.execute(
            """SELECT kind, status, count(*) AS calls,
                      COALESCE(sum(input_tokens), 0) AS input_tokens,
                      COALESCE(sum(output_tokens), 0) AS output_tokens,
                      round(sum(cost_usd), 4) AS est_cost_usd
               FROM ai_calls GROUP BY kind, status ORDER BY kind, status"""
        ).fetchall()
        for r in rows:
            print(
                f"  {r['kind']:8} {r['status']:17} calls={r['calls']:3} "
                f"in={r['input_tokens']:7} out={r['output_tokens']:6} est=${r['est_cost_usd']}"
            )


if __name__ == "__main__":
    main()
