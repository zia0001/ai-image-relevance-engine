"""Data layer: every SQL query the API needs. No business rules here."""
import psycopg


def list_articles(conn: psycopg.Connection):
    return conn.execute(
        """SELECT a.id, a.title, m.subject, m.category, m.confidence
           FROM articles a LEFT JOIN article_metadata m ON m.article_id = a.id ORDER BY a.id"""
    ).fetchall()


def get_article(conn: psycopg.Connection, article_id: int):
    return conn.execute(
        """SELECT a.id, a.title, m.subject, m.category, m.confidence, e.vector
           FROM articles a JOIN article_metadata m ON m.article_id = a.id
           JOIN article_embeddings e ON e.article_id = a.id WHERE a.id = %s""",
        (article_id,),
    ).fetchone()


_IMAGE_SQL = """SELECT i.id, i.filename, m.subject, m.category, m.confidence, m.needs_review, e.vector
                FROM images i JOIN image_metadata m ON m.image_id = i.id
                JOIN image_embeddings e ON e.image_id = i.id"""


def list_images(conn: psycopg.Connection):
    return conn.execute(_IMAGE_SQL).fetchall()


def get_image(conn: psycopg.Connection, image_id: int):
    return conn.execute(_IMAGE_SQL + " WHERE i.id = %s", (image_id,)).fetchone()


_SUGGESTION_SQL = """SELECT s.id, s.article_id, s.image_id, i.filename, s.similarity, s.rank,
                            s.guard_decision, s.guard_rule, s.reason,
                            r.decision AS review_decision, r.note AS review_note, r.reviewed_at
                     FROM suggestions s JOIN images i ON i.id = s.image_id
                     LEFT JOIN reviews r ON r.suggestion_id = s.id"""


def save_suggestions(conn: psycopg.Connection, article_id: int, candidates: list[dict]) -> None:
    """Upsert the candidates. Old suggestions drop out unless a human already reviewed them."""
    for c in candidates:
        d = c["decision"]
        conn.execute(
            """INSERT INTO suggestions (article_id, image_id, similarity, rank, guard_decision, guard_rule, reason)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (article_id, image_id) DO UPDATE SET
                   similarity = EXCLUDED.similarity, rank = EXCLUDED.rank,
                   guard_decision = EXCLUDED.guard_decision, guard_rule = EXCLUDED.guard_rule,
                   reason = EXCLUDED.reason""",
            (article_id, c["image"]["id"], c["similarity"], c["rank"],
             "accepted" if d.accepted else "rejected", d.rule, d.reason),
        )
    keep = [c["image"]["id"] for c in candidates]
    conn.execute(
        """DELETE FROM suggestions s WHERE s.article_id = %s AND s.image_id <> ALL(%s)
           AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.suggestion_id = s.id)""",
        (article_id, keep),
    )


def list_suggestions(conn: psycopg.Connection, article_id: int):
    return conn.execute(_SUGGESTION_SQL + " WHERE s.article_id = %s ORDER BY s.rank", (article_id,)).fetchall()


def get_suggestion(conn: psycopg.Connection, suggestion_id: int):
    return conn.execute(_SUGGESTION_SQL + " WHERE s.id = %s", (suggestion_id,)).fetchone()


def upsert_review(conn: psycopg.Connection, suggestion_id: int, decision: str, note: str | None) -> None:
    """One review per suggestion: sending the same review again changes nothing."""
    conn.execute(
        """INSERT INTO reviews (suggestion_id, decision, note) VALUES (%s, %s, %s)
           ON CONFLICT (suggestion_id) DO UPDATE SET
               decision = EXCLUDED.decision, note = EXCLUDED.note, reviewed_at = now()""",
        (suggestion_id, decision, note),
    )


def cost_summary(conn: psycopg.Connection):
    return conn.execute(
        """SELECT kind, status, count(*)::int AS calls,
                  COALESCE(sum(input_tokens), 0)::int AS input_tokens,
                  COALESCE(sum(output_tokens), 0)::int AS output_tokens,
                  COALESCE(sum(cost_usd), 0)::float8 AS cost_usd
           FROM ai_calls GROUP BY kind, status ORDER BY kind, status"""
    ).fetchall()


def image_status(conn: psycopg.Connection):
    """Progress of the vision job: image counts by status and the images that failed."""
    counts = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, count(*)::int AS n FROM images GROUP BY status").fetchall()}
    failed = conn.execute("SELECT filename, last_error FROM images WHERE status = 'failed' ORDER BY id").fetchall()
    return counts, failed
