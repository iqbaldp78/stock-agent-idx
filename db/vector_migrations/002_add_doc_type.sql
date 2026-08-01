-- Add doc_type column to news_signals table to support both news and report documents
ALTER TABLE news_signals ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) DEFAULT 'news';
CREATE INDEX IF NOT EXISTS idx_news_signals_doc_type ON news_signals(doc_type);
