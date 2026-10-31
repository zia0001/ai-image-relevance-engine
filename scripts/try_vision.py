"""Send ONE image to Gemini and show what comes back.
Run:  python -m scripts.try_vision data/images/some_photo.jpg"""
import sys
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.image_analysis import ImageAnalysis

MODEL = get_settings().vision_model
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

PROMPT = """You are labelling photos of animals for a content library.
Look at the image and return ONE JSON object with exactly these keys:

- "subject": short lowercase name of the main animal, 3-30 characters, e.g. "red fox"
- "category": one of "fox", "wolf", "dog", "bear", "deer", "other".
  Use "other" for any animal not in that list, or when no animal is visible.
- "attributes": list of 1-10 short visual descriptors, each under 40 characters
- "caption": one sentence (10-500 characters) describing the image and naming the animal
- "confidence": number from 0 to 1, how sure you are about subject and category.
  Use a value below 0.6 if the image is blurry, partly hidden, or the animal is hard to
  tell apart from a similar one (for example fox vs dog vs wolf).

Return only the JSON object, no other text."""


def main() -> None:
    path = Path(sys.argv[1])
    client = genai.Client(api_key=get_settings().gemini_api_key, http_options=types.HttpOptions(timeout=60_000))
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=path.read_bytes(), mime_type=MIME[path.suffix.lower()]),
            PROMPT,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
    )
    print("RAW RESPONSE:")
    print(response.text)

    usage = response.usage_metadata
    print(
        f"\nTOKENS: input={usage.prompt_token_count} "
        f"output={usage.candidates_token_count} thinking={usage.thoughts_token_count}"
    )

    try:
        result = ImageAnalysis.model_validate_json(response.text)
        print("\nVALID:", result)
    except ValidationError as exc:
        print("\nREJECTED by ImageAnalysis:")
        print(exc)


if __name__ == "__main__":
    main()
