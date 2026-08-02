-- Add sentiment_score column (1-10) to news_signals table
ALTER TABLE news_signals ADD COLUMN IF NOT EXISTS sentiment_score SMALLINT DEFAULT 5;
CREATE INDEX IF NOT EXISTS idx_news_signals_sentiment_score ON news_signals(sentiment_score);
