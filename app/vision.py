"""The vision step: ask Gemini about an image, validate the answer, log every call."""
import time
from pathlib import Path

import httpx
import psycopg
from google.genai import errors, types
from pydantic import ValidationError

from app.config import Settings
from app.costs import log_call
from app.prompts import IMAGE_PROMPT
from app.schemas.image_analysis import ImageAnalysis

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# Worth retrying: quota exceeded (429) and server trouble (500, 503, 504).
# Anything else (bad key, unknown model, bad request) fails again, so we stop at once.
RETRYABLE = {429, 500, 503, 504}


def retry_delay_seconds(exc: errors.APIError) -> float | None:
    """On a 429, Google says how long to wait, e.g. 'retryDelay': '24s'."""
    try:
        for item in exc.details["error"]["details"]:
            if item.get("@type", "").endswith("RetryInfo"):
                return float(item["retryDelay"].rstrip("s"))
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    return None


def _ms(started: float) -> int:
    return int((time.time() - started) * 1000)


def analyze_image(conn: psycopg.Connection, client, settings: Settings, image: dict):
    """Ask the model about one image, up to settings.max_attempts times.

    Every attempt, good or bad, is written to ai_calls.
    Returns (analysis, raw_text, error). On success error is None; on failure analysis is None.
    """
    path = Path(image["path"])
    mime = MIME.get(path.suffix.lower())
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, None, f"cannot read file: {exc}"
    if mime is None:
        return None, None, f"unsupported file type: {path.suffix}"

    last_error = "no attempt was made"
    for attempt in range(1, settings.max_attempts + 1):
        started = time.time()
        try:
            response = client.models.generate_content(
                model=settings.vision_model,
                contents=[types.Part.from_bytes(data=data, mime_type=mime), IMAGE_PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
        except errors.APIError as exc:
            last_error = f"{exc.code}: {str(exc)[:200]}"
            log_call(conn, settings, kind="vision", status="api_error", attempt=attempt,
                     image_id=image["id"], error=last_error, latency_ms=_ms(started))
            if exc.code not in RETRYABLE:
                break
            if "PerDay" in str(exc.details):
                last_error = "daily free-tier quota used up: " + last_error
                break
            if attempt < settings.max_attempts:
                wait = min(max(retry_delay_seconds(exc) or 0, settings.seconds_between_calls), 90)
                print(f"    {image['filename']}: attempt {attempt} failed ({exc.code}), waiting {wait:.0f}s", flush=True)
                time.sleep(wait)
            continue
        except httpx.TransportError as exc:
            # timeout or dropped connection: no HTTP answer at all, but worth retrying
            last_error = f"network: {type(exc).__name__}"
            log_call(conn, settings, kind="vision", status="api_error", attempt=attempt,
                     image_id=image["id"], error=last_error, latency_ms=_ms(started))
            print(f"    {image['filename']}: attempt {attempt} failed ({last_error})", flush=True)
            if attempt < settings.max_attempts:
                time.sleep(settings.seconds_between_calls)
            continue

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else None
        # thinking tokens are billed as output, so they count too
        output_tokens = (
            (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else None
        )
        try:
            analysis = ImageAnalysis.model_validate_json(response.text or "")
        except ValidationError as exc:
            e = exc.errors()[0]; last_error = f"model output rejected: {list(e['loc'])} {e['msg']}"
            log_call(conn, settings, kind="vision", status="validation_error", attempt=attempt,
                     image_id=image["id"], input_tokens=input_tokens, output_tokens=output_tokens,
                     error=last_error, latency_ms=_ms(started))
            continue

        log_call(conn, settings, kind="vision", status="ok", attempt=attempt, image_id=image["id"],
                 input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=_ms(started))
        return analysis, response.text, None

    return None, None, last_error


def run_vision_batch(conn: psycopg.Connection, client, settings: Settings, limit: int | None = None) -> dict:
    """Process every pending (or previously failed) image. Safe to run again."""
    # An interrupted run leaves its image stuck as 'processing'; put those back.
    conn.execute("UPDATE images SET status = 'pending' WHERE status = 'processing'")
    rows = conn.execute(
        "SELECT id, filename, path FROM images WHERE status IN ('pending', 'failed') ORDER BY id"
    ).fetchall()
    if limit:
        rows = rows[:limit]

    summary = {"done": 0, "failed": 0, "flagged": 0, "skipped": 0}
    for n, image in enumerate(rows, 1):
        # Claim the image. If another run already took it, no row matches and we skip it.
        claimed = conn.execute(
            "UPDATE images SET status = 'processing', last_error = NULL "
            "WHERE id = %s AND status IN ('pending', 'failed') RETURNING id",
            (image["id"],),
        ).fetchone()
        if claimed is None:
            summary["skipped"] += 1
            continue

        analysis, raw, error = analyze_image(conn, client, settings, image)
        if analysis is None:
            conn.execute(
                "UPDATE images SET status = 'failed', last_error = %s WHERE id = %s",
                (error, image["id"]),
            )
            summary["failed"] += 1
            print(f"[{n}/{len(rows)}] {image['filename']:18} FAILED  {error}")
        else:
            needs_review = analysis.confidence < settings.min_confidence
            conn.execute(
                """INSERT INTO image_metadata
                       (image_id, subject, category, attributes, caption, confidence,
                        needs_review, raw_response)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (image_id) DO UPDATE SET
                       subject = EXCLUDED.subject, category = EXCLUDED.category,
                       attributes = EXCLUDED.attributes, caption = EXCLUDED.caption,
                       confidence = EXCLUDED.confidence, needs_review = EXCLUDED.needs_review,
                       raw_response = EXCLUDED.raw_response, analyzed_at = now()""",
                (image["id"], analysis.subject, analysis.category.value, analysis.attributes,
                 analysis.caption, analysis.confidence, needs_review, raw),
            )
            conn.execute("UPDATE images SET status = 'done' WHERE id = %s", (image["id"],))
            summary["done"] += 1
            summary["flagged"] += int(needs_review)
            flag = "  NEEDS REVIEW" if needs_review else ""
            print(
                f"[{n}/{len(rows)}] {image['filename']:18} {analysis.category.value:6} "
                f"conf={analysis.confidence:.2f}  {analysis.subject}{flag}"
            )
        if n < len(rows):
            time.sleep(settings.seconds_between_calls)
    return summary
