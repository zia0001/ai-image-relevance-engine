import psycopg

from app.config import Settings


def estimate_cost(settings: Settings, input_tokens: int | None, output_tokens: int | None) -> float:
    """Estimated USD for one call from its token counts, at list price."""
    inp = input_tokens or 0
    out = output_tokens or 0
    return (inp * settings.vision_input_rate + out * settings.vision_output_rate) / 1_000_000


def log_call(
    conn: psycopg.Connection,
    settings: Settings,
    *,
    kind: str,
    status: str,
    attempt: int,
    image_id: int | None = None,
    article_id: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    error: str | None = None,
    latency_ms: int | None = None,
) -> None:
    """Write ONE row to ai_calls for ONE attempt, whether it worked or not."""
    conn.execute(
        """INSERT INTO ai_calls (kind, image_id, article_id, model, input_tokens, output_tokens,
                                 cost_usd, status, attempt, error, latency_ms)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            kind, image_id, article_id, settings.vision_model, input_tokens, output_tokens,
            round(estimate_cost(settings, input_tokens, output_tokens), 6),
            status, attempt, error, latency_ms,
        ),
    )
