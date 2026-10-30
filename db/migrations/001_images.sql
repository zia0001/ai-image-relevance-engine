-- One row per image file.
CREATE TABLE images (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL UNIQUE,
    path        TEXT NOT NULL,
    source_url  TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- What the vision model said about an image, after Pydantic validated it.
CREATE TABLE image_metadata (
    image_id      INTEGER PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    subject       TEXT NOT NULL,
    category      TEXT NOT NULL
                  CHECK (category IN ('fox', 'wolf', 'dog', 'bear', 'deer', 'other')),
    attributes    TEXT[] NOT NULL,
    caption       TEXT NOT NULL,
    confidence    REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    needs_review  BOOLEAN NOT NULL DEFAULT FALSE,
    raw_response  TEXT,
    analyzed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);