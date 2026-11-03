"""Load data/articles.json into the articles table. Safe to re-run."""
import json

from app.db import connect


def main() -> None:
    articles = json.load(open("data/articles.json", encoding="utf-8"))
    with connect() as conn:
        for a in articles:
            conn.execute(
                "INSERT INTO articles (title, body) VALUES (%s, %s) ON CONFLICT (title) DO NOTHING",
                (a["title"], a["body"]),
            )
        n = conn.execute("SELECT count(*) AS n FROM articles").fetchone()["n"]
    print(f"articles in database: {n}")


if __name__ == "__main__":
    main()
