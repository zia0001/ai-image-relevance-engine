-- One embedding per image, made from its caption.
CREATE TABLE image_embeddings (
    image_id    INTEGER PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    dims        INTEGER NOT NULL,
    vector      DOUBLE PRECISION[] NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One embedding per article, made from its text.
CREATE TABLE article_embeddings (
    article_id  INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    model       TEXT NOT NULL,
    dims        INTEGER NOT NULL,
    vector      DOUBLE PRECISION[] NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The cost log: ONE ROW PER AI CALL, including failures and retries.
-- A call that fails twice and then succeeds is three rows.
CREATE TABLE ai_calls (
    id             SERIAL PRIMARY KEY,
    kind           TEXT NOT NULL
                   CHECK (kind IN ('vision', 'image_embedding', 'article_embedding', 'article_analysis')),
    image_id       INTEGER REFERENCES images(id) ON DELETE SET NULL,
    article_id     INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    model          TEXT NOT NULL,
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    cost_usd       NUMERIC(12, 6) NOT NULL DEFAULT 0,
    status         TEXT NOT NULL CHECK (status IN ('ok', 'api_error', 'validation_error')),
    attempt        INTEGER NOT NULL DEFAULT 1,
    error          TEXT,
    latency_ms     INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_calls_kind ON ai_calls (kind);