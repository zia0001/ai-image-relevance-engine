"""Shapes of what the API returns."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PostOut(BaseModel):
    id: int
    title: str
    subject: str | None
    category: str | None
    confidence: float | None


class DecisionOut(BaseModel):
    accepted: bool
    rule: str
    reason: str


class CandidateOut(BaseModel):
    rank: int
    image_id: int
    filename: str
    subject: str
    category: str
    similarity: float
    decision: DecisionOut


class RankedImages(BaseModel):
    post_id: int
    title: str
    verdict: Literal["match", "no_confident_match"]
    best_image_id: int | None
    message: str
    candidates: list[CandidateOut]


class CheckOut(BaseModel):
    post_id: int
    image_id: int
    filename: str
    similarity: float
    decision: DecisionOut


class ReviewIn(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)


class SuggestionOut(BaseModel):
    id: int
    post_id: int
    image_id: int
    filename: str
    rank: int
    similarity: float
    guard_decision: Literal["accepted", "rejected"]
    guard_rule: str
    reason: str
    review_decision: str | None
    review_note: str | None
    reviewed_at: datetime | None


class CostRow(BaseModel):
    kind: str
    status: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostSummary(BaseModel):
    rows: list[CostRow]
    total_calls: int
    total_cost_usd: float


class FailedImage(BaseModel):
    filename: str
    last_error: str | None


class ImageStatus(BaseModel):
    total: int
    counts: dict[str, int]
    failed: list[FailedImage]
