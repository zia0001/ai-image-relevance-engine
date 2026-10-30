"""Convert downloaded images (.avif etc.) to .jpg so Gemini can read them.
Run from the repo root:  python -m scripts.convert_images   (safe to run again)"""
from pathlib import Path

from PIL import Image

IMAGES_DIR = Path("data/images")
CONVERT = {".avif", ".jfif", ".bmp", ".tif", ".tiff", ".gif"}
MAX_WIDTH = 1600  # smaller files, same result for our purposes


def main() -> None:
    converted = 0
    for src in sorted(IMAGES_DIR.iterdir()):
        if src.suffix.lower() not in CONVERT:
            continue
        dst = src.with_suffix(".jpg")
        if dst.exists():
            print(f"skipped {src.name}: {dst.name} already exists")
            continue
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)))
            im.save(dst, "JPEG", quality=85)
        src.unlink()  # remove the original once the .jpg is saved
        converted += 1
        print(f"converted {src.name} -> {dst.name}")
    print(f"{converted} file(s) converted")


if __name__ == "__main__":
    main()
