from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.image_analysis import Category


class ArticleAnalysis(BaseModel):
    """What an article is about, in the same shape as an image, so the guard can compare them."""

    subject: Annotated[str, StringConstraints(min_length=3, max_length=30, to_lower=True, strip_whitespace=True)]
    category: Category
    confidence: float = Field(ge=0, le=1)
