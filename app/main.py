"""HTTP layer: validates input, calls the data and logic layers, shapes the response."""
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from app import repo
from app.config import get_settings
from app.db import connect
from app.guard import check_pair
from app.matching import match_article
from app.schemas.api import (CandidateOut, CheckOut, CostRow, CostSummary, DecisionOut, PostOut,
                             RankedImages, ReviewIn, SuggestionOut)
from app.similarity import cosine

app = FastAPI(title="Image relevance engine")


def _decision(d) -> DecisionOut:
    return DecisionOut(accepted=d.accepted, rule=d.rule, reason=d.reason)


@app.get("/health")
def health():
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/posts", response_model=list[PostOut])
def list_posts():
    with connect() as conn:
        return repo.list_articles(conn)


@app.get("/posts/{post_id}/images", response_model=RankedImages)
def ranked_images(post_id: int, top_k: int | None = Query(default=None, ge=1, le=20)):
    s = get_settings()
    with connect() as conn:
        article = repo.get_article(conn, post_id)
        if article is None:
            raise HTTPException(404, "post not found, or not analyzed and embedded yet")
        images = repo.list_images(conn)
    candidates, best = match_article(
        article, images, min_confidence=s.min_confidence,
        min_similarity=s.min_similarity, top_k=top_k or s.top_k)
    out = [
        CandidateOut(rank=c["rank"], image_id=c["image"]["id"], filename=c["image"]["filename"],
                     subject=c["image"]["subject"], category=c["image"]["category"],
                     similarity=round(c["similarity"], 4), decision=_decision(c["decision"]))
        for c in candidates
    ]
    if best:
        return RankedImages(post_id=post_id, title=article["title"], verdict="match",
                            best_image_id=best["image"]["id"],
                            message=f"Suggested {best['image']['filename']}", candidates=out)
    rules = sorted({c["decision"].rule for c in candidates})
    return RankedImages(
        post_id=post_id, title=article["title"], verdict="no_confident_match", best_image_id=None,
        message="No confident match found. Every top candidate was rejected (" + ", ".join(rules) + ").",
        candidates=out)


@app.get("/posts/{post_id}/check/{image_id}", response_model=CheckOut)
def check_candidate(post_id: int, image_id: int):
    """Force one specific image onto a post and see the guard's verdict."""
    s = get_settings()
    with connect() as conn:
        article = repo.get_article(conn, post_id)
        image = repo.get_image(conn, image_id)
    if article is None or image is None:
        raise HTTPException(404, "post or image not found, or not analyzed and embedded yet")
    sim = cosine(article["vector"], image["vector"])
    d = check_pair(article, image, sim, min_confidence=s.min_confidence, min_similarity=s.min_similarity)
    return CheckOut(post_id=post_id, image_id=image_id, filename=image["filename"],
                    similarity=round(sim, 4), decision=_decision(d))


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Write endpoints need the key from .env. No key configured on the server: refuse everything."""
    expected = get_settings().review_api_key
    if not expected:
        raise HTTPException(503, "review API key is not configured on the server")
    if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "missing or invalid API key")


def _suggestion_out(row) -> SuggestionOut:
    return SuggestionOut(
        id=row["id"], post_id=row["article_id"], image_id=row["image_id"], filename=row["filename"],
        rank=row["rank"], similarity=round(row["similarity"], 4), guard_decision=row["guard_decision"],
        guard_rule=row["guard_rule"], reason=row["reason"], review_decision=row["review_decision"],
        review_note=row["review_note"], reviewed_at=row["reviewed_at"])


@app.post("/posts/{post_id}/suggestions", response_model=list[SuggestionOut],
          dependencies=[Depends(require_api_key)])
def create_suggestions(post_id: int):
    """Run matching and the guard for a post and save the verdicts so a human can review them."""
    s = get_settings()
    with connect() as conn:
        article = repo.get_article(conn, post_id)
        if article is None:
            raise HTTPException(404, "post not found, or not analyzed and embedded yet")
        candidates, _ = match_article(
            article, repo.list_images(conn), min_confidence=s.min_confidence,
            min_similarity=s.min_similarity, top_k=s.top_k)
        repo.save_suggestions(conn, post_id, candidates)
        return [_suggestion_out(r) for r in repo.list_suggestions(conn, post_id)]


@app.get("/posts/{post_id}/suggestions", response_model=list[SuggestionOut])
def get_suggestions(post_id: int):
    with connect() as conn:
        return [_suggestion_out(r) for r in repo.list_suggestions(conn, post_id)]


@app.get("/suggestions/{suggestion_id}", response_model=SuggestionOut)
def inspect_suggestion(suggestion_id: int):
    """Why was this image selected or refused? The rule, the reason and any review are all here."""
    with connect() as conn:
        row = repo.get_suggestion(conn, suggestion_id)
    if row is None:
        raise HTTPException(404, "suggestion not found")
    return _suggestion_out(row)


@app.post("/suggestions/{suggestion_id}/review", response_model=SuggestionOut,
          dependencies=[Depends(require_api_key)])
def review_suggestion(suggestion_id: int, body: ReviewIn):
    with connect() as conn:
        row = repo.get_suggestion(conn, suggestion_id)
        if row is None:
            raise HTTPException(404, "suggestion not found")
        if body.decision == "approved" and row["guard_decision"] == "rejected":
            raise HTTPException(409, f"cannot approve: the guard rejected this pair "
                                     f"[{row['guard_rule']}] {row['reason']}")
        repo.upsert_review(conn, suggestion_id, body.decision, body.note)
        return _suggestion_out(repo.get_suggestion(conn, suggestion_id))


@app.get("/costs", response_model=CostSummary)
def costs():
    """Every AI call is logged with its cost; this is the per-kind, per-status summary."""
    with connect() as conn:
        rows = repo.cost_summary(conn)
    return CostSummary(rows=[CostRow(**r) for r in rows], total_calls=sum(r["calls"] for r in rows),
                       total_cost_usd=round(sum(r["cost_usd"] for r in rows), 6))
