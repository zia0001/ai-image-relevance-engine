from app.matching import match_article

KW = dict(min_confidence=0.6, min_similarity=0.74, top_k=5)
ARTICLE = {"category": "fox", "subject": "red fox", "confidence": 0.95, "vector": [1.0, 0.0]}


def img(i, category, subject, vector, **override):
    d = {"id": i, "filename": f"img_{i}.jpg", "category": category, "subject": subject,
         "confidence": 0.95, "needs_review": False, "vector": vector}
    d.update(override)
    return d


def test_wolf_that_looks_closest_is_skipped_for_the_fox():
    images = [img(1, "fox", "red fox", [0.9, 0.436]), img(2, "fox", "red fox", [0.8, 0.6]),
              img(3, "wolf", "gray wolf", [0.99, 0.141])]
    candidates, best = match_article(ARTICLE, images, **KW)
    assert candidates[0]["image"]["id"] == 3 and candidates[0]["decision"].rule == "category"
    assert best["image"]["id"] == 1


def test_no_confident_match_when_only_wrong_categories_exist():
    images = [img(1, "wolf", "gray wolf", [0.95, 0.312]), img(2, "bear", "brown bear", [0.9, 0.436])]
    candidates, best = match_article(ARTICLE, images, **KW)
    assert best is None
    assert all(c["decision"].rule == "category" for c in candidates)


def test_similarity_below_threshold_is_refused():
    candidates, best = match_article(ARTICLE, [img(1, "fox", "red fox", [0.5, 0.866])], **KW)
    assert best is None and candidates[0]["decision"].rule == "similarity"


def test_flagged_image_is_not_suggested():
    images = [img(1, "fox", "red fox", [0.95, 0.312], needs_review=True, confidence=0.5),
              img(2, "fox", "red fox", [0.8, 0.6])]
    candidates, best = match_article(ARTICLE, images, **KW)
    assert candidates[0]["decision"].rule == "image_confidence"
    assert best["image"]["id"] == 2


def test_top_k_limits_the_candidates():
    images = [img(i, "fox", "red fox", [0.9, 0.436]) for i in range(1, 9)]
    candidates, _ = match_article(ARTICLE, images, min_confidence=0.6, min_similarity=0.74, top_k=3)
    assert len(candidates) == 3


def test_other_category_needs_the_same_subject():
    article = {"category": "other", "subject": "red kangaroo", "confidence": 0.95, "vector": [1.0, 0.0]}
    images = [img(1, "other", "giraffe", [0.95, 0.312]), img(2, "other", "kangaroo", [0.85, 0.527])]
    candidates, best = match_article(article, images, **KW)
    assert candidates[0]["decision"].rule == "subject"
    assert best["image"]["subject"] == "kangaroo"
