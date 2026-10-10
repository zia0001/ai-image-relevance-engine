from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
        FOX = "fox"
        WOLF = "wolf"
        DOG = "dog"
        BEAR = "bear"
        DEER = "deer"

class ImageAnalysis(BaseModel):
    subject: str
    category: Category
    attributes: list[str]
    caption: str
    confidence: float = Field(ge=0, le=1)


if __name__ == "__main__":

    
    # test = ImageAnalysis(
    #     subject="deer",
    #     category=Category.DEER,
    #     attributes=["brown fur", "wild", "forest"],
    #     caption="A brown deer standing in a forest",
    #     confidence=1.1,
    # )
    # print(test)

    from pydantic import ValidationError
    try:
        bad = ImageAnalysis(
            subject="cat",
            category="cat",  # This will raise a validation error because "cat" is not a valid Category
            attributes=["brown fur", "wild", "forest"],
            caption="A brown cat standing in a forest",
            confidence=1,
        )
        print(bad)

    except ValidationError as e:
        print("Validation failed as expected:")
        print(e)