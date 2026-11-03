import pytest
from pydantic import ValidationError

from app.schemas.article_analysis import ArticleAnalysis
from app.schemas.image_analysis import ImageAnalysis


def valid(**override):
    data = dict(subject="red fox", category="fox", attributes=["orange fur", "wild"],
                caption="A red fox standing in a forest", confidence=0.94)
    data.update(override)
    return data


def test_valid_output_is_accepted():
    assert ImageAnalysis(**valid()).category.value == "fox"


@pytest.mark.parametrize("field,value", [
    ("confidence", 1.4), ("confidence", -0.1), ("category", "cat"),
    ("attributes", []), ("attributes", ["x"] * 11), ("attributes", [""]),
    ("subject", "dg"), ("caption", "short"), ("caption", "x" * 501),
])
def test_each_broken_rule_is_rejected(field, value):
    with pytest.raises(ValidationError):
        ImageAnalysis(**valid(**{field: value}))


def test_malformed_json_and_missing_fields_are_rejected():
    with pytest.raises(ValidationError):
        ImageAnalysis.model_validate_json("this is not json")
    with pytest.raises(ValidationError):
        ImageAnalysis.model_validate_json('{"subject": "red fox"}')


def test_subject_is_lowercased_and_trimmed():
    assert ImageAnalysis(**valid(subject="  Red Fox ")).subject == "red fox"


def test_article_analysis_rejects_unknown_category():
    ArticleAnalysis(subject="red fox", category="fox", confidence=0.9)
    with pytest.raises(ValidationError):
        ArticleAnalysis(subject="red fox", category="cat", confidence=0.9)
