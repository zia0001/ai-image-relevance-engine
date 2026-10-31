"""Try several Gemini models with a tiny text prompt and report which answer quickly."""
import time

from google import genai
from google.genai import types

from app.config import get_settings

CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3.8-flash",
]

client = genai.Client(
    api_key=get_settings().gemini_api_key,
    http_options=types.HttpOptions(timeout=20_000),  # 20 seconds each
)

for model in CANDIDATES:
    start = time.time()
    try:
        reply = client.models.generate_content(model=model, contents="Reply with the single word OK")
        print(f"OK     {model:30} {time.time() - start:5.1f}s  -> {reply.text.strip()[:20]}")
    except Exception as exc:
        print(f"FAILED {model:30} {time.time() - start:5.1f}s  -> {type(exc).__name__}: {str(exc)[:90]}")
