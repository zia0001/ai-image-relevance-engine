"""Correct one image's human label.  python -m scripts.set_truth FILE CATEGORY SUBJECT"""
import json
import sys
from pathlib import Path

CATEGORIES = {"fox", "wolf", "dog", "bear", "deer", "other"}


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[2] not in CATEGORIES:
        raise SystemExit("usage: python -m scripts.set_truth FILE CATEGORY SUBJECT   (category: " + ", ".join(sorted(CATEGORIES)) + ")")
    path = Path("data/image_truth.json")
    truth = json.loads(path.read_text(encoding="utf-8"))
    if sys.argv[1] not in truth:
        raise SystemExit(f"{sys.argv[1]} is not in the truth file")
    truth[sys.argv[1]] = {"category": sys.argv[2], "subject": sys.argv[3].lower()}
    path.write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{sys.argv[1]} -> {sys.argv[2]} / {sys.argv[3].lower()}")


if __name__ == "__main__":
    main()
