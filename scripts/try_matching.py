"""NAIVE matching: rank all images by similarity for each article, with no guard yet.
Shows what similarity alone gets right and wrong."""
import json

from app.db import connect
from app.similarity import cosine


def main() -> None:
    expected = {a["title"]: a["expected"] for a in json.load(open("data/articles.json", encoding="utf-8"))}
    with connect() as conn:
        articles = conn.execute(
            """SELECT a.title, e.vector FROM articles a
               JOIN article_embeddings e ON e.article_id = a.id ORDER BY a.id"""
        ).fetchall()
        images = conn.execute(
            """SELECT i.filename, m.category, m.subject, e.vector FROM images i
               JOIN image_metadata m ON m.image_id = i.id
               JOIN image_embeddings e ON e.image_id = i.id"""
        ).fetchall()
    for a in articles:
        ranked = sorted(((cosine(a["vector"], im["vector"]), im) for im in images),
                        key=lambda t: t[0], reverse=True)[:3]
        print(f"\n{a['title']}\n  expected: {expected.get(a['title'], '?')}")
        for score, im in ranked:
            print(f"    {score:.3f}  {im['filename']:16} {im['category']:6} {im['subject']}")


if __name__ == "__main__":
    main()
