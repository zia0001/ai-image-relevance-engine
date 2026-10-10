# Evidence

Proof that each piece works, with real terminal output.

## Phase 1: ImageAnalysis schema (`app/schemas/image_analysis.py`)

Every Gemini response must pass through this model before it is trusted. Each rule below was tested by sending data that breaks exactly that rule and confirming Pydantic rejects it with a `ValidationError`.

### confidence above 1 is rejected

Rule: `confidence: float = Field(ge=0, le=1)`

```
1 validation error for ImageAnalysis
confidence
  Input should be less than or equal to 1 [type=less_than_equal, input_value=1.4, input_type=float]
    For further information visit https://errors.pydantic.dev/2.13/v/less_than_equal
```

### category outside the enum is rejected

Rule: `category: Category`, where `Category(str, Enum)` allows only fox, wolf, dog, bear, deer.

```
1 validation error for ImageAnalysis
category
  Input should be 'fox', 'wolf', 'dog', 'bear' or 'deer' [type=enum, input_value='cat', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/enum
```

Note: `Category.CAT` raises `AttributeError` in Python before Pydantic runs. The test must pass the raw string `"cat"`, which is what Gemini's JSON would contain.

### attributes: list length is enforced

Rule: `attributes: list[...] = Field(min_length=1, max_length=10)`

Too many items (excerpt of the output):

```
attributes
  List should have at most 10 items after validation, not 12 [type=too_long, input_value=['', 'wild', 'forest', 'd...independent', 'curious'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.13/v/too_long
```

Empty list:

```
attributes
  List should have at least 1 item after validation, not 0 [type=too_short, input_value=[], input_type=list]
    For further information visit https://errors.pydantic.dev/2.13/v/too_short
```

### attributes: blank items are rejected

Rule: each item is `Annotated[str, Field(min_length=1, max_length=40)]`. The `.0` in the path shows which item failed.

```
attributes.0
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

### subject: too short is rejected

Rule: `StringConstraints(min_length=3, max_length=30, to_lower=True, strip_whitespace=True)`

```
subject
  String should have at least 3 characters [type=string_too_short, input_value='dg', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

### subject is lowercased

Input was `subject="Dog"`. Output:

```
subject='dog' category=<Category.DOG: 'dog'> attributes=['domestic', 'playful', 'cute', 'furry', 'small', 'agile', 'nocturnal', 'independent', 'curious'] caption='Hanging on the fence' confidence=1.0
```

The caption keeps its capital H on purpose: it feeds the embedding, so it is not lowercased.

### caption: empty and oversized are rejected

Rule: `StringConstraints(min_length=..., max_length=500, strip_whitespace=True)`

Empty caption (run when the minimum was 3; being raised to 10):

```
caption
  String should have at least 3 characters [type=string_too_short, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

Oversized caption:

```
1 validation error for ImageAnalysis
caption
  String should have at most 500 characters [type=string_too_long, input_value='Hang onHang onHang onHan...onHang onHang onHang on', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_long
```

## Findings worth remembering

- `to_lower` is not a valid argument for `Field()`. Pydantic warned that extra keyword arguments are deprecated and ignored it. The correct tool is `StringConstraints`.
- `min_length` counts characters for a string and items for a list. The list and the strings inside it need separate rules.
- A test should break exactly one rule at a time, otherwise the error does not show which rule fired.


