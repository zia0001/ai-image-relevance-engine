"""Sanity-check the embeddings.
Run:  python -m scripts.try_similarity [filename]   (default fox_02.jpg)"""
import sys
from collections import defaultdict

from app.db import connect
from app.similarity import cosine


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "fox_02.jpg"
    with connect() as conn:
        rows = conn.execute(
            """SELECT i.filename, m.category, m.subject, e.vector
               FROM images i
               JOIN image_metadata m ON m.image_id = i.id
               JOIN image_embeddings e ON e.image_id = i.id ORDER BY i.id"""
        ).fetchall()

    target = next((r for r in rows if r["filename"] == query), None)
    if target is None:
        raise SystemExit(f"{query} has no embedding")

    print(f"Closest images to {query} ({target['category']}, {target['subject']}):")
    scored = sorted(
        ((cosine(target["vector"], r["vector"]), r) for r in rows if r["filename"] != query),
        key=lambda t: t[0], reverse=True,
    )
    for score, r in scored[:6]:
        print(f"  {score:.3f}  {r['filename']:16} {r['category']:6} {r['subject']}")
    print("  ...")
    for score, r in scored[-2:]:
        print(f"  {score:.3f}  {r['filename']:16} {r['category']:6} {r['subject']}")

    # Average similarity between categories: which groups look alike to the model?
    sums, counts = defaultdict(float), defaultdict(int)
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            key = tuple(sorted((a["category"], b["category"])))
            sums[key] += cosine(a["vector"], b["vector"])
            counts[key] += 1
    cats = sorted({r["category"] for r in rows})
    print("\nAverage similarity between categories:")
    print("        " + "".join(f"{c:>8}" for c in cats))
    for c1 in cats:
        cells = "".join(f"{sums[tuple(sorted((c1, c2)))] / counts[tuple(sorted((c1, c2)))]:8.3f}" for c2 in cats)
        print(f"{c1:8}{cells}")


if __name__ == "__main__":
    main()
