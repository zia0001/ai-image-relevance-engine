"""Turn text into a vector with Gemini, with retries and one ai_calls row per attempt."""
import math
import time

import httpx
import psycopg
from google.genai import errors, types

from app.config import Settings
from app.costs import log_call
from app.vision import RETRYABLE


def normalize(vec: list[float]) -> list[float]:
    """Scale a vector to length 1. Gemini only does this itself at full size (3072 dims),
    and we ask for 768, so we do it. With length-1 vectors, cosine similarity is a dot product."""
    length = math.sqrt(sum(x * x for x in vec))
    return [x / length for x in vec]


def embed_text(conn: psycopg.Connection, client, settings: Settings, text: str, *,
               kind: str, image_id: int | None = None, article_id: int | None = None):
    """Returns (vector, error). Exactly one of them is None."""
    # The embedding response reports no token usage, so we estimate (about 4 characters per token).
    est_tokens = max(1, len(text) // 4)
    cost = est_tokens * settings.embedding_input_rate / 1_000_000
    last_error = "no attempt was made"
    for attempt in range(1, 4):
        started = time.time()
        try:
            result = client.models.embed_content(
                model=settings.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="SEMANTIC_SIMILARITY", output_dimensionality=settings.embedding_dims
                ),
            )
            vector = normalize(list(result.embeddings[0].values))
        except (errors.APIError, httpx.TransportError) as exc:
            code = getattr(exc, "code", None)
            last_error = f"{code}: {str(exc)[:150]}" if code else f"network: {type(exc).__name__}"
            log_call(conn, settings, kind=kind, status="api_error", attempt=attempt, image_id=image_id,
                     article_id=article_id, error=last_error, model=settings.embedding_model,
                     cost_usd=0.0, latency_ms=int((time.time() - started) * 1000))
            if code is not None and code not in RETRYABLE:
                break
            time.sleep(5 * attempt)
            continue
        log_call(conn, settings, kind=kind, status="ok", attempt=attempt, image_id=image_id,
                 article_id=article_id, input_tokens=est_tokens, output_tokens=0,
                 model=settings.embedding_model, cost_usd=cost,
                 latency_ms=int((time.time() - started) * 1000))
        return vector, None
    return None, last_error
