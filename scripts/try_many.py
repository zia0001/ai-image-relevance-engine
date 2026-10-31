"""Run Gemini on several images and print one summary line each, retrying on server errors.
Run:  python -m scripts.try_many blurry lookalike other
(arguments are filename prefixes; with none it uses blurry, lookalike and other)"""
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.image_analysis import ImageAnalysis
from scripts.try_vision import MIME, PROMPT

settings = get_settings()
client = genai.Client(
    api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=60_000)
)
MAX_ATTEMPTS = 3


def analyze(path: Path):
    """Returns (response or None, attempts used)."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=settings.vision_model,
                contents=[
                    types.Part.from_bytes(data=path.read_bytes(), mime_type=MIME[path.suffix.lower()]),
                    PROMPT,
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
            return response, attempt
        except errors.ServerError as exc:
            print(f"  {path.name}: attempt {attempt} failed ({getattr(exc, 'code', '?')}), retrying...")
            time.sleep(4 * attempt)
    return None, MAX_ATTEMPTS


def main() -> None:
    prefixes = sys.argv[1:] or ["blurry", "lookalike", "other"]
    files = sorted(
        p
        for p in Path("data/images").iterdir()
        if p.suffix.lower() in MIME and any(p.name.startswith(x) for x in prefixes)
    )
    for path in files:
        response, attempts = analyze(path)
        if response is None:
            print(f"{path.name:18} FAILED after {attempts} attempts")
            continue
        try:
            result = ImageAnalysis.model_validate_json(response.text)
            print(f"{path.name:18} {result.category.value:6} conf={result.confidence:.2f}  {result.subject}")
        except ValidationError as exc:
            print(f"{path.name:18} REJECTED by schema ({exc.error_count()} error(s))")


if __name__ == "__main__":
    main()
