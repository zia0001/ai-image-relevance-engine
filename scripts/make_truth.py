"""Create data/image_truth.json: the HUMAN ground truth for each image.
Pre-filled from the filename prefix (your own label when you downloaded it) and, for the
odd groups, from the model. It lists the images you must open and confirm.
Run once:  python -m scripts.make_truth   (never overwrites an existing file)"""
import json
from pathlib import Path

from app.db import connect

CLASSES = {"fox", "wolf", "dog", "bear", "deer"}
PREFIX_TO_CLASS = {"lookalike": "dog"}  # the lookalike_* images are huskies


def main() -> None:
    out = Path("data/image_truth.json")
    if out.exists():
        raise SystemExit("data/image_truth.json already exists, not overwriting")
    with connect() as conn:
        rows = conn.execute(
            """SELECT i.filename, m.category, m.subject FROM images i
               JOIN image_metadata m ON m.image_id = i.id ORDER BY i.filename"""
        ).fetchall()
    truth, review = {}, []
    for r in rows:
        prefix = r["filename"].split("_")[0]
        cls = PREFIX_TO_CLASS.get(prefix, prefix)
        if cls in CLASSES:
            truth[r["filename"]] = {"category": cls, "subject": r["subject"]}
            if r["category"] != cls:
                review.append(r)
        else:
            truth[r["filename"]] = {"category": r["category"], "subject": r["subject"]}
            review.append(r)
    out.write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} with {len(truth)} images\n")
    print("OPEN THESE IMAGES and check the label (prefix says one thing / model says another, or no prefix class):")
    for r in review:
        print(f"  {r['filename']:18} model says: {r['category']:6} / {r['subject']}")
    print("\nIf one is wrong, fix it with:  python -m scripts.set_truth FILE CATEGORY SUBJECT")
    print("example:  python -m scripts.set_truth wolf_4.jpg wolf 'gray wolf'")


if __name__ == "__main__":
    main()
