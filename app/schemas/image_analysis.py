from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class Category(str, Enum):
    FOX = "fox"
    WOLF = "wolf"
    DOG = "dog"
    BEAR = "bear"
    DEER = "deer"
    OTHER = "other"


class ImageAnalysis(BaseModel):
    subject: Annotated[str, StringConstraints(min_length=3, max_length=30, to_lower=True, strip_whitespace=True)]
    category: Category
    attributes: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(min_length=1, max_length=10)
    caption: Annotated[str, StringConstraints(min_length=10, max_length=500, strip_whitespace=True)]
    confidence: float = Field(ge=0, le=1)
