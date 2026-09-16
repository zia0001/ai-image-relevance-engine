from pydantic import BaseModel, Field

class ImageAnalysis(BaseModel):
    subject: str
    category: str
    attributes: list[str]
    caption: str
    confidence: float = Field(ge=0, le=1)


if __name__ == "__main__":
    test = ImageAnalysis(
        subject="red fox",
        category="animal",
        attributes=["orange fur", "wild", "forest"],
        caption="A red fox standing in a forest",
        confidence=0.94,
    )
    print(test)

    from pydantic import ValidationError
    try:
        bad = ImageAnalysis(
            subject="red fox",
            category="animal",
            attributes=["orange fur", "wild", "forest"],
            caption="A red fox standing in a forest",
            confidence=1.4,
        )
    except ValidationError as e:
        print("Validation failed as expected:")
        print(e)