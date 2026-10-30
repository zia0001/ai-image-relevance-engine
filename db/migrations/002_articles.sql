-- The blog posts we want to find images for.
CREATE TABLE articles (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL UNIQUE,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- What an article is about, in the same terms as image_metadata,
-- so the mismatch guard can compare an image and an article directly.
CREATE TABLE article_metadata (
    article_id    INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    subject       TEXT NOT NULL,
    category      TEXT NOT NULL
                  CHECK (category IN ('fox', 'wolf', 'dog', 'bear', 'deer', 'other')),
    confidence    REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    raw_response  TEXT,
    analyzed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);