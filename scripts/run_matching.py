"""Rank images for every article, apply the guard, save the verdicts to suggestions.
Run:  python -m scripts.run_matching   (safe to re-run: an article's old suggestions are replaced)"""
import json

from app.config import get_settings
from app.db import connect
from app.guard import head_noun
from app.matching import match_article


def preview_correct(expected: str, best) -> bool:
    """Rough check using the MODEL's labels (circular). The real eval uses human labels."""
    if expected == "none":
        return best is None
    if best is None:
        return False
    image = best["image"]
    return expected == image["category"] or head_noun(expected) == head_noun(image["subject"])


def main() -> None:
    settings = get_settings()
    expected = {a["title"]: a["expected"] for a in json.load(open("data/articles.json", encoding="utf-8"))}
    with connect() as conn:
        articles = conn.execute(
            """SELECT a.id, a.title, m.subject, m.category, m.confidence, e.vector
               FROM articles a JOIN article_metadata m ON m.article_id = a.id
               JOIN article_embeddings e ON e.article_id = a.id ORDER BY a.id"""
        ).fetchall()
        images = conn.execute(
            """SELECT i.id, i.filename, m.subject, m.category, m.confidence, m.needs_review, e.vector
               FROM images i JOIN image_metadata m ON m.image_id = i.id
               JOIN image_embeddings e ON e.image_id = i.id"""
        ).fetchall()

        correct = 0
        for a in articles:
            candidates, best = match_article(
                a, images, min_confidence=settings.min_confidence,
                min_similarity=settings.min_similarity, top_k=settings.top_k)
            conn.execute("DELETE FROM suggestions WHERE article_id = %s", (a["id"],))
            for c in candidates:
                d = c["decision"]
                conn.execute(
                    """INSERT INTO suggestions (article_id, image_id, similarity, rank,
                                                guard_decision, guard_rule, reason)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (a["id"], c["image"]["id"], c["similarity"], c["rank"],
                     "accepted" if d.accepted else "rejected", d.rule, d.reason))
            ok = preview_correct(expected.get(a["title"], "?"), best)
            correct += ok
            verdict = f"MATCH {best['image']['filename']} ({best['similarity']:.3f})" if best else "NO CONFIDENT MATCH"
            print(f"\n{'OK ' if ok else 'BAD'} {a['title'][:55]}  [{a['category']}: {a['subject']}, expected {expected.get(a['title'], '?')}]")
            print(f"    -> {verdict}")
            for c in candidates[:3]:
                d = c["decision"]
                tag = "accepted" if d.accepted else f"rejected [{d.rule}]"
                print(f"       #{c['rank']} {c['similarity']:.3f} {c['image']['filename']:16} {tag}: {d.reason[:95]}")
        print(f"\nPreview (model labels, not the real eval): {correct} of {len(articles)} as expected")


if __name__ == "__main__":
    main()
