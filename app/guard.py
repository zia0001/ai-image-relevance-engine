"""The mismatch guard: may this image be suggested for this article?

Pure functions: no database, no network. Rules run in order and the FIRST failure
rejects the pair with a plain-English reason.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    accepted: bool
    rule: str  # which rule decided: article_confidence, image_confidence, category, subject, similarity, accepted
    reason: str


def head_noun(subject: str) -> str:
    """Last word of a subject, trailing plural 's' removed: 'red kangaroo' -> 'kangaroo'."""
    word = subject.strip().split()[-1]
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


STOPWORDS = {"red", "gray", "grey", "white", "black", "brown", "wild", "common", "giant",
             "little", "small", "big", "young", "baby", "pet", "domestic", "the"}


def _words(subject: str) -> set[str]:
    """Meaningful words of a subject, singularised: 'goat farming' -> {'goat', 'farming'}."""
    out = set()
    for w in subject.lower().split():
        if w in STOPWORDS:
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 3 else w)
    return out


def subjects_match(a: str, b: str) -> bool:
    """True if two subjects share a meaningful word."""
    return bool(_words(a) & _words(b))


def check_pair(article: dict, image: dict, similarity: float, *,
               min_confidence: float, min_similarity: float) -> Decision:
    if article["confidence"] < min_confidence:
        return Decision(False, "article_confidence",
                        f"article analysis is not confident enough ({article['confidence']:.2f} < {min_confidence})")
    if image["needs_review"]:
        return Decision(False, "image_confidence",
                        f"image was labelled with low confidence ({image['confidence']:.2f}); a human must review it first")
    if article["category"] != image["category"]:
        return Decision(False, "category",
                        f"category mismatch: article is about {article['category']} ('{article['subject']}'), "
                        f"image shows {image['category']} ('{image['subject']}')")
    if article["category"] == "other" and not subjects_match(article["subject"], image["subject"]):
        return Decision(False, "subject",
                        f"both are 'other' but the subjects differ: '{article['subject']}' vs '{image['subject']}'")
    if similarity < min_similarity:
        return Decision(False, "similarity", f"similarity {similarity:.3f} is below the threshold {min_similarity}")
    return Decision(True, "accepted",
                    f"category '{image['category']}' matches and similarity {similarity:.3f} >= {min_similarity}")
