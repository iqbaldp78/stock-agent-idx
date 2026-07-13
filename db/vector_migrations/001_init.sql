CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS news_signals (
    id SERIAL PRIMARY KEY,
    stream_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    content TEXT NOT NULL,
    summary TEXT,
    sentiment VARCHAR(50),
    impact_scope VARCHAR(50),
    tickers JSONB,
    embedding halfvec(3072)
);
CREATE INDEX ON news_signals USING hnsw (embedding halfvec_cosine_ops);
