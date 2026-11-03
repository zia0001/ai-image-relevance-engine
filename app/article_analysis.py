"""Ask Gemini what an article is about, validate the answer, log every call."""
import time

import httpx
import psycopg
from google.genai import errors, types
from pydantic import ValidationError

from app.config import Settings
from app.costs import log_call
from app.prompts import ARTICLE_PROMPT
from app.schemas.article_analysis import ArticleAnalysis
from app.vision import RETRYABLE, _ms, retry_delay_seconds


def analyze_article(conn: psycopg.Connection, client, settings: Settings, article: dict):
    """Returns (analysis, raw_text, error), same contract as analyze_image."""
    prompt = f"{ARTICLE_PROMPT}\n\nTitle: {article['title']}\n\n{article['body']}"
    last_error = "no attempt was made"
    for attempt in range(1, settings.max_attempts + 1):
        started = time.time()
        try:
            response = client.models.generate_content(
                model=settings.vision_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
        except (errors.APIError, httpx.TransportError) as exc:
            code = getattr(exc, "code", None)
            last_error = f"{code}: {str(exc)[:200]}" if code else f"network: {type(exc).__name__}"
            log_call(conn, settings, kind="article_analysis", status="api_error", attempt=attempt,
                     article_id=article["id"], error=last_error, latency_ms=_ms(started))
            if code is not None and code not in RETRYABLE:
                break
            if "PerDay" in str(getattr(exc, "details", "")):
                last_error = "daily free-tier quota used up: " + last_error
                break
            if attempt < settings.max_attempts:
                wait = min(max((retry_delay_seconds(exc) if code else None) or 0,
                               settings.seconds_between_calls), 90)
                print(f"    attempt {attempt} failed ({code or 'network'}), waiting {wait:.0f}s", flush=True)
                time.sleep(wait)
            continue

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else None
        output_tokens = (
            (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else None
        )
        try:
            analysis = ArticleAnalysis.model_validate_json(response.text or "")
        except ValidationError as exc:
            e = exc.errors()[0]
            last_error = f"model output rejected: {list(e['loc'])} {e['msg']}"
            log_call(conn, settings, kind="article_analysis", status="validation_error", attempt=attempt,
                     article_id=article["id"], input_tokens=input_tokens, output_tokens=output_tokens,
                     error=last_error, latency_ms=_ms(started))
            continue
        log_call(conn, settings, kind="article_analysis", status="ok", attempt=attempt,
                 article_id=article["id"], input_tokens=input_tokens, output_tokens=output_tokens,
                 latency_ms=_ms(started))
        return analysis, response.text, None
    return None, None, last_error
