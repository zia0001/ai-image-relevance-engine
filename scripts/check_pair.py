"""Force ONE image onto ONE article and show the guard's verdict (acceptance probe 3).
Run:  python -m scripts.check_pair "How red foxes survive" wolf_01.jpg"""
import sys

from app.config import get_settings
from app.db import connect
from app.guard import check_pair
from app.similarity import cosine


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: python -m scripts.check_pair "WORDS FROM ARTICLE TITLE" IMAGE_FILENAME')
    words, filename = sys.argv[1], sys.argv[2]
    s = get_settings()
    with connect() as conn:
        a = conn.execute(
            """SELECT a.title, m.subject, m.category, m.confidence, e.vector FROM articles a
               JOIN article_metadata m ON m.article_id = a.id
               JOIN article_embeddings e ON e.article_id = a.id
               WHERE a.title ILIKE %s ORDER BY a.id LIMIT 1""", (f"%{words}%",)).fetchone()
        im = conn.execute(
            """SELECT i.filename, m.subject, m.category, m.confidence, m.needs_review, e.vector FROM images i
               JOIN image_metadata m ON m.image_id = i.id
               JOIN image_embeddings e ON e.image_id = i.id WHERE i.filename = %s""", (filename,)).fetchone()
    if not a or not im:
        raise SystemExit("article or image not found")
    sim = cosine(a["vector"], im["vector"])
    d = check_pair(a, im, sim, min_confidence=s.min_confidence, min_similarity=s.min_similarity)
    print(f"Article:   {a['title']}  [{a['category']}: {a['subject']}]")
    print(f"Candidate: {im['filename']}  [{im['category']}: {im['subject']}]  similarity {sim:.3f}")
    print(f"Verdict:   {'ACCEPTED' if d.accepted else 'REJECTED'} [{d.rule}]")
    print(f"Reason:    {d.reason}")


if __name__ == "__main__":
    main()
