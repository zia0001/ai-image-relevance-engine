from app.guard import check_pair, head_noun

KW = dict(min_confidence=0.6, min_similarity=0.77)


def article(category="fox", subject="red fox", confidence=0.95):
    return {"category": category, "subject": subject, "confidence": confidence}


def image(category="fox", subject="red fox", confidence=0.98, needs_review=False):
    return {"category": category, "subject": subject, "confidence": confidence, "needs_review": needs_review}


def test_accepts_matching_pair():
    d = check_pair(article(), image(), 0.85, **KW)
    assert d.accepted and d.rule == "accepted"


def test_rejects_category_mismatch_even_with_high_similarity():
    d = check_pair(article(), image(category="wolf", subject="gray wolf"), 0.95, **KW)
    assert not d.accepted and d.rule == "category"
    assert "fox" in d.reason and "wolf" in d.reason


def test_rejects_low_similarity_in_same_category():
    d = check_pair(article(), image(), 0.70, **KW)
    assert not d.accepted and d.rule == "similarity"


def test_rejects_image_flagged_for_review():
    d = check_pair(article(), image(confidence=0.5, needs_review=True), 0.9, **KW)
    assert not d.accepted and d.rule == "image_confidence"


def test_rejects_unclear_article():
    d = check_pair(article(confidence=0.4), image(), 0.9, **KW)
    assert not d.accepted and d.rule == "article_confidence"


def test_other_category_needs_same_subject():
    assert not check_pair(article("other", "red kangaroo"), image("other", "giraffe"), 0.9, **KW).accepted
    assert check_pair(article("other", "red kangaroo"), image("other", "kangaroo"), 0.9, **KW).accepted


def test_head_noun():
    assert head_noun("red kangaroo") == "kangaroo"
    assert head_noun("coyote") == "coyote"


def test_subjects_match_ignores_colours_and_extra_words():
    from app.guard import subjects_match
    assert subjects_match("goat farming", "goat")
    assert subjects_match("grey wolf", "gray wolf")
    assert not subjects_match("carbon markets", "goat")
    assert not subjects_match("red panda", "red kangaroo")
