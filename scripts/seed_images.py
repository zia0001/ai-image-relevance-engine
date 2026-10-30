"""Register every image file in data/images/ in the database. Safe to run twice."""
from pathlib import Path

from app.db import connect

IMAGES_DIR = Path("data/images")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def seed_images() -> tuple[int, int]:
    """Returns (newly added, files found)."""
    if not IMAGES_DIR.is_dir():
        raise SystemExit(f"Folder {IMAGES_DIR}/ not found. Create it and add some photos.")
    files = sorted(p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in EXTENSIONS)
    added = 0
    with connect() as conn:
        for path in files:
            cur = conn.execute(
                "INSERT INTO images (filename, path) VALUES (%s, %s) "
                "ON CONFLICT (filename) DO NOTHING",
                (path.name, str(path)),
            )
            added += cur.rowcount
    return added, len(files)


if __name__ == "__main__":
    added, found = seed_images()
    print(f"{added} new image(s) added, {found} file(s) found, {found - added} already registered")
