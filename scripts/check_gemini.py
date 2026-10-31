"""Check the Gemini key, connection and model names, with a 30-second timeout."""
import time

from google import genai
from google.genai import types

from app.config import get_settings

MODEL = "gemini-3.8-flash"

client = genai.Client(
    api_key=get_settings().gemini_api_key,
    http_options=types.HttpOptions(timeout=30_000),  # milliseconds
)

start = time.time()
print("Listing available models...")
names = [m.name for m in client.models.list()]
print(f"{len(names)} models found in {time.time() - start:.1f}s")
for name in names:
    if "flash" in name or "embedding" in name:
        print("  ", name)

start = time.time()
print(f"\nText-only call to {MODEL}...")
reply = client.models.generate_content(model=MODEL, contents="Reply with the single word OK")
print("Reply:", reply.text, f"({time.time() - start:.1f}s)")
