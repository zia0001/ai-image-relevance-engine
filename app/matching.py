from app.guard import check_pair
from app.similarity import cosine


def match_article(article: dict, images: list[dict], *, min_confidence: float,
                  min_similarity: float, top_k: int):
    """Rank every image by similarity, run the guard on the top_k.

    Returns (candidates, best). best is the first accepted candidate, or None,
    which means 'no confident match'.
    """
    ranked = sorted(((cosine(article["vector"], im["vector"]), im) for im in images),
                    key=lambda t: t[0], reverse=True)[:top_k]
    candidates = []
    for rank, (similarity, image) in enumerate(ranked, 1):
        decision = check_pair(article, image, similarity,
                              min_confidence=min_confidence, min_similarity=min_similarity)
        candidates.append({"rank": rank, "image": image, "similarity": similarity, "decision": decision})
    best = next((c for c in candidates if c["decision"].accepted), None)
    return candidates, best
