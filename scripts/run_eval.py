"""Measure the matcher against HUMAN ground truth.
Article truth: the 'expected' field in data/articles.json.
Image truth:   data/image_truth.json (what you verified by looking).
Run:  python -m scripts.run_eval"""
import json

from app.config import get_settings
from app.db import connect
from app.guard import subjects_match
from app.matching import match_article
from app.similarity import cosine


def is_correct(expected: str, category: str, subject: str) -> bool:
    return expected == category or subjects_match(expected, subject)


def evaluate(articles, images, expected, *, min_confidence, min_similarity, top_k):
    r = {"returned": 0, "correct": 0, "matchable": 0, "none": 0, "refused": 0,
         "wrong": [], "missed": [], "false_accepts": []}
    for a in articles:
        exp = expected[a["title"]]
        candidates, best = match_article(a, images, min_confidence=min_confidence,
                                         min_similarity=min_similarity, top_k=top_k)
        if exp == "none":
            r["none"] += 1
            if best is None:
                r["refused"] += 1
                r.setdefault("refusals", []).append((a["title"], candidates[0]))
            else:
                r["returned"] += 1
                r["false_accepts"].append((a["title"], best))
        else:
            r["matchable"] += 1
            if best is None:
                r["missed"].append((a["title"], exp, candidates[0]))
            else:
                r["returned"] += 1
                im = best["image"]
                if is_correct(exp, im["true_category"], im["true_subject"]):
                    r["correct"] += 1
                else:
                    r["wrong"].append((a["title"], exp, best))
    return r


def main() -> None:
    s = get_settings()
    expected = {a["title"]: a["expected"] for a in json.load(open("data/articles.json", encoding="utf-8"))}
    truth = json.load(open("data/image_truth.json", encoding="utf-8"))
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
    for im in images:
        im["true_category"] = truth[im["filename"]]["category"]
        im["true_subject"] = truth[im["filename"]]["subject"]

    kw = dict(min_confidence=s.min_confidence, top_k=s.top_k)
    r = evaluate(articles, images, expected, min_similarity=s.min_similarity, **kw)
    precision = r["correct"] / r["returned"] if r["returned"] else 0.0
    recall = r["correct"] / r["matchable"] if r["matchable"] else 0.0

    print(f"EVAL SET: {len(articles)} articles ({r['matchable']} have a correct image, {r['none']} have none), "
          f"{len(images)} images")
    all_right = r["correct"] + r["refused"]
    print(f"\nHEADLINE TOP-1 PRECISION (brief definition: share of ALL {len(articles)} articles with the right outcome): "
          f"{all_right / len(articles):.1%}  ({r['correct']} right images + {r['refused']} right refusals)")
    print(f"\nWITH GUARD (similarity threshold {s.min_similarity}, top_k {s.top_k})")
    print(f"  matches returned:      {r['returned']}")
    print(f"  correct matches:       {r['correct']}")
    print(f"  TOP-1 PRECISION:       {precision:.1%}   ({r['correct']} of {r['returned']} returned matches)")
    print(f"  recall:                {recall:.1%}   ({r['correct']} of {r['matchable']} articles with a correct image)")
    print(f"  correct refusals:      {r['refused']} of {r['none']} articles with no image")
    for title, exp, best in r["wrong"]:
        im = best["image"]
        print(f"  WRONG        {title[:48]}: expected {exp}, got {im['filename']} "
              f"(truth {im['true_category']}/{im['true_subject']}, sim {best['similarity']:.3f})")
    for title, exp, top in r["missed"]:
        print(f"  MISSED       {title[:48]}: expected {exp}; best candidate rejected [{top['decision'].rule}] "
              f"{top['decision'].reason[:80]}")
    for title, best in r["false_accepts"]:
        print(f"  FALSE ACCEPT {title[:48]}: matched {best['image']['filename']} ({best['similarity']:.3f})")

    for title, top in r.get("refusals", []):
        print(f"  REFUSED      {title[:48]}: [{top['decision'].rule}] {top['decision'].reason[:70]}")
    base = 0
    base_wrong = []
    for a in articles:
        exp = expected[a["title"]]
        if exp == "none":
            continue
        top = max(images, key=lambda im: cosine(a["vector"], im["vector"]))
        if is_correct(exp, top["true_category"], top["true_subject"]):
            base += 1
        else:
            base_wrong.append(f"  BASELINE WRONG: {a['title'][:48]}: expected {exp}, top-1 was "
                              f"{top['filename']} ({top['true_category']}/{top['true_subject']})")
    print(f"\nBASELINE, no guard (top-1 by similarity only)")
    for line in base_wrong:
        print(line)
    print(f"  correct on articles with an image: {base} of {r['matchable']}")
    print(f"  articles with no image: 0 of {r['none']} refused (it always returns something)")

    print("\nTHRESHOLD SWEEP")
    for t in [0.70, 0.74, 0.76, 0.77, 0.78, 0.79, 0.80, 0.82]:
        x = evaluate(articles, images, expected, min_similarity=t, **kw)
        p = x["correct"] / x["returned"] if x["returned"] else 0.0
        print(f"  {t:.2f}  returned={x['returned']:2}  correct={x['correct']:2}  precision={p:5.1%}  "
              f"recall={x['correct'] / x['matchable']:5.1%}  refused_none={x['refused']}/{x['none']}")


if __name__ == "__main__":
    main()
