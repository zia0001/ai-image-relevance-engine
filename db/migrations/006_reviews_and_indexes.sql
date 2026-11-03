CREATE TABLE IF NOT EXISTS reviews (
    id             SERIAL PRIMARY KEY,
    suggestion_id  INTEGER NOT NULL UNIQUE REFERENCES suggestions(id) ON DELETE CASCADE,
    decision       TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    note           TEXT,
    reviewer       TEXT NOT NULL DEFAULT 'api',
    reviewed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_suggestions_article_rank ON suggestions (article_id, rank);
CREATE INDEX IF NOT EXISTS idx_ai_calls_kind_status ON ai_calls (kind, status);
CREATE INDEX IF NOT EXISTS idx_ai_calls_image ON ai_calls (image_id);
CREATE INDEX IF NOT EXISTS idx_ai_calls_article ON ai_calls (article_id);
CREATE INDEX IF NOT EXISTS idx_images_status ON images (status);
CREATE INDEX IF NOT EXISTS idx_metadata_category ON image_metadata (category);
