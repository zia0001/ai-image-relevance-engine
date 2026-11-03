CREATE TABLE IF NOT EXISTS suggestions (
    id              SERIAL PRIMARY KEY,
    article_id      INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    image_id        INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    similarity      REAL NOT NULL,
    rank            INTEGER NOT NULL,
    guard_decision  TEXT NOT NULL CHECK (guard_decision IN ('accepted', 'rejected')),
    guard_rule      TEXT NOT NULL DEFAULT '',
    reason          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (article_id, image_id)
);
ALTER TABLE suggestions ADD COLUMN IF NOT EXISTS guard_rule TEXT NOT NULL DEFAULT '';
