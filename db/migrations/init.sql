-- db/migrations/init.sql
-- Stock Agent IDX — PostgreSQL Schema

-- Universe saham
CREATE TABLE IF NOT EXISTS universe (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(10) NOT NULL UNIQUE,
    is_lq45    BOOLEAN DEFAULT TRUE,
    is_custom  BOOLEAN DEFAULT FALSE,
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hasil scoring tiap agent
CREATE TABLE IF NOT EXISTS agent_scores (
    id                SERIAL PRIMARY KEY,
    run_date          DATE NOT NULL,
    ticker            VARCHAR(10) NOT NULL,
    fundamental_score NUMERIC(4,2),
    technical_score   NUMERIC(4,2),
    bandarm_score     NUMERIC(4,2),
    macro_signal      VARCHAR(20),
    composite_score   NUMERIC(4,2),
    weight_mode       VARCHAR(20),
    weights_used      JSONB,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Akumulasi broker harian (rolling 30 hari)
CREATE TABLE IF NOT EXISTS broker_accumulation (
    id           SERIAL PRIMARY KEY,
    ticker       VARCHAR(10) NOT NULL,
    trade_date   DATE NOT NULL,
    broker_code  VARCHAR(10) NOT NULL,
    broker_name  VARCHAR(100),
    buy_lot      BIGINT DEFAULT 0,
    buy_value    BIGINT DEFAULT 0,
    avg_price    NUMERIC(12,2),
    sell_lot     BIGINT DEFAULT 0,
    sell_value   BIGINT DEFAULT 0,
    foreign_net  BIGINT DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, trade_date, broker_code)
);

-- View: avg cost bandar 7 hari
CREATE OR REPLACE VIEW v_broker_avg_7d AS
SELECT
    ticker,
    broker_code,
    broker_name,
    SUM(buy_lot)                                        AS total_buy_lot,
    SUM(buy_value)                                      AS total_buy_value,
    ROUND(SUM(buy_value)::numeric /
          NULLIF(SUM(buy_lot), 0) / 100, 2)             AS avg_price_7d,
    COUNT(DISTINCT trade_date)                          AS active_days,
    MAX(trade_date)                                     AS last_active
FROM broker_accumulation
WHERE trade_date >= CURRENT_DATE - INTERVAL '10 days'
  AND buy_lot > 0
GROUP BY ticker, broker_code, broker_name
ORDER BY total_buy_value DESC;

-- View: avg cost bandar 1 bulan (true cost)
CREATE OR REPLACE VIEW v_broker_avg_1m AS
SELECT
    ticker,
    broker_code,
    broker_name,
    SUM(buy_lot)                                        AS total_buy_lot,
    SUM(buy_value)                                      AS total_buy_value,
    ROUND(SUM(buy_value)::numeric /
          NULLIF(SUM(buy_lot), 0) / 100, 2)             AS avg_price_1m,
    COUNT(DISTINCT trade_date)                          AS active_days,
    COUNT(DISTINCT trade_date) * 100.0 /
        NULLIF((SELECT COUNT(DISTINCT trade_date)
         FROM broker_accumulation b2
         WHERE b2.ticker = broker_accumulation.ticker
           AND b2.trade_date >= CURRENT_DATE - INTERVAL '30 days'), 0)
                                                        AS consistency_pct
FROM broker_accumulation
WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
  AND buy_lot > 0
GROUP BY ticker, broker_code, broker_name
ORDER BY total_buy_value DESC;

-- Log debate
CREATE TABLE IF NOT EXISTS debate_logs (
    id         SERIAL PRIMARY KEY,
    run_date   DATE NOT NULL,
    ticker     VARCHAR(10) NOT NULL,
    round      INTEGER NOT NULL,
    agent      VARCHAR(50) NOT NULL,
    argument   TEXT,
    vote       VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Final signals
CREATE TABLE IF NOT EXISTS signals (
    id               SERIAL PRIMARY KEY,
    run_date         DATE NOT NULL,
    ticker           VARCHAR(10) NOT NULL,
    rank             INTEGER,
    signal           TEXT,
    entry_low        NUMERIC(12,2),
    entry_high       NUMERIC(12,2),
    max_entry        NUMERIC(12,2),
    target_1         NUMERIC(12,2),
    target_2         NUMERIC(12,2),
    target_3         NUMERIC(12,2),
    stop_loss        NUMERIC(12,2),
    risk_reward      NUMERIC(5,2),
    conviction       TEXT,
    thesis           TEXT,
    entry_reasoning  TEXT,
    bandar_avg_7d    NUMERIC(12,2),
    bandar_avg_1m    NUMERIC(12,2),
    broker_utama     TEXT,
    time_horizon     TEXT,
    weight_mode      TEXT,
    composite_score  NUMERIC(4,2),
    ml_prediction    JSONB,
    price_prediction JSONB,
    tp_position_sizing JSONB,
    broker_true_costs JSONB,
    broker_distributors JSONB,
    risk_reward_tp1  VARCHAR(20),
    risk_reward_tp2  VARCHAR(20),
    risk_reward_tp3  VARCHAR(20),
    created_at       TIMESTAMP DEFAULT NOW()
);

-- Performance tracking
CREATE TABLE IF NOT EXISTS performance (
    id           SERIAL PRIMARY KEY,
    signal_id    INTEGER REFERENCES signals(id),
    check_date   DATE NOT NULL,
    actual_price NUMERIC(12,2),
    result       VARCHAR(20),
    return_pct   NUMERIC(6,2),
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_broker_ticker_date ON broker_accumulation(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_signals_run_date   ON signals(run_date);
CREATE INDEX IF NOT EXISTS idx_scores_run_date    ON agent_scores(run_date, ticker);
CREATE INDEX IF NOT EXISTS idx_debate_run_date    ON debate_logs(run_date, ticker);

-- IHSG Predictions
CREATE TABLE IF NOT EXISTS ihsg_predictions (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    current_price NUMERIC(12,2) NOT NULL,
    confidence VARCHAR(10),
    direction VARCHAR(30),
    volatility_level VARCHAR(20),
    day_1_price NUMERIC(12,2),
    day_1_pct NUMERIC(6,2),
    day_3_price NUMERIC(12,2),
    day_3_pct NUMERIC(6,2),
    day_5_price NUMERIC(12,2),
    day_5_pct NUMERIC(6,2),
    day_7_price NUMERIC(12,2),
    day_7_pct NUMERIC(6,2),
    reasoning TEXT,
    key_drivers JSONB,
    risks JSONB,
    component_scores JSONB,
    ihsg_trend VARCHAR(30),
    macro_signal VARCHAR(30),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ihsg_run_date ON ihsg_predictions(run_date DESC);

-- ============================================================
-- Raw Data Cache Tables
-- ============================================================

-- Cache: OHLCV harian per ticker (sumber: Stockbit / yfinance)
CREATE TABLE IF NOT EXISTS ohlcv_prices (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open       NUMERIC(12,2),
    high       NUMERIC(12,2),
    low        NUMERIC(12,2),
    close      NUMERIC(12,2),
    volume     BIGINT,
    source     VARCHAR(20) DEFAULT 'stockbit',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, trade_date)
);

-- Cache: IHSG OHLCV harian (^JKSE, up to 8 tahun)
CREATE TABLE IF NOT EXISTS ihsg_ohlcv (
    id         SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    open       NUMERIC(12,2),
    high       NUMERIC(12,2),
    low        NUMERIC(12,2),
    close      NUMERIC(12,2),
    volume     BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cache: Fundamental snapshot harian per ticker
CREATE TABLE IF NOT EXISTS stock_info_snapshot (
    id                    SERIAL PRIMARY KEY,
    ticker                VARCHAR(10) NOT NULL,
    snapshot_date         DATE NOT NULL,
    per                   NUMERIC(10,4),
    pbv                   NUMERIC(10,4),
    roe                   NUMERIC(10,4),
    der                   NUMERIC(10,4),
    market_cap            NUMERIC(20,2),
    current_price         NUMERIC(12,2),
    revenue_growth        NUMERIC(10,4),
    earnings_growth       NUMERIC(10,4),
    high_52w              NUMERIC(12,2),
    low_52w               NUMERIC(12,2),
    dividend_yield        NUMERIC(10,4),
    dividend_payout_ratio NUMERIC(10,4),
    dividend_per_share    NUMERIC(12,4),
    net_income_history    JSONB,
    eps_history           JSONB,
    revenue_history       JSONB,
    extra_data            JSONB,
    created_at            TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, snapshot_date)
);

-- Cache: Sektor indeks OHLCV harian (^JKFINA, ^JKMING, dst)
CREATE TABLE IF NOT EXISTS sector_ohlcv (
    id          SERIAL PRIMARY KEY,
    sector_code VARCHAR(20) NOT NULL,
    trade_date  DATE NOT NULL,
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(sector_code, trade_date)
);

-- Marker tanggal IHSG yang tidak ada data (libur IDX, tidak ada trading)
CREATE TABLE IF NOT EXISTS ihsg_no_data (
    id         SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Marker tanggal yang sudah dicoba fetch tapi memang tidak ada data (libur/suspensi)
CREATE TABLE IF NOT EXISTS ohlcv_no_data (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    source     VARCHAR(20) DEFAULT 'stockbit',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, trade_date, source)
);

-- Extend broker_accumulation untuk support cache (broker_type & day_foreign_net)
ALTER TABLE broker_accumulation ADD COLUMN IF NOT EXISTS broker_type    VARCHAR(10);
ALTER TABLE broker_accumulation ADD COLUMN IF NOT EXISTS day_foreign_net BIGINT DEFAULT 0;

-- Extend signals untuk kolom yang ditambahkan setelah initial schema
ALTER TABLE signals ADD COLUMN IF NOT EXISTS price_prediction JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS tp_position_sizing JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker_true_costs JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker_distributors JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS bandar_avg_7d    NUMERIC(12,2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS bandar_avg_1m    NUMERIC(12,2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker_utama     TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS time_horizon     TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS target_2         NUMERIC(12,2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS risk_reward      NUMERIC(5,2);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ml_prediction    JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS risk_reward_tp1  VARCHAR(20);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS risk_reward_tp2  VARCHAR(20);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS risk_reward_tp3  VARCHAR(20);
ALTER TABLE signals ALTER COLUMN signal TYPE TEXT;
ALTER TABLE signals ALTER COLUMN conviction TYPE TEXT;
ALTER TABLE signals ALTER COLUMN time_horizon TYPE TEXT;
ALTER TABLE signals ALTER COLUMN weight_mode TYPE TEXT;

-- Indexes untuk cache tables
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON ohlcv_prices(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_ohlcv_no_data_ticker_date ON ohlcv_no_data(ticker, trade_date);
CREATE INDEX IF NOT EXISTS idx_ihsg_ohlcv_date   ON ihsg_ohlcv(trade_date);
CREATE INDEX IF NOT EXISTS idx_ihsg_no_data_date  ON ihsg_no_data(trade_date);
CREATE INDEX IF NOT EXISTS idx_stock_info_snap   ON stock_info_snapshot(ticker, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_sector_ohlcv_date ON sector_ohlcv(sector_code, trade_date);

-- Seed: Universe LQ45
INSERT INTO universe (ticker, is_lq45, is_custom, active) VALUES
('ACES', TRUE, FALSE, TRUE),
('ADRO', TRUE, FALSE, TRUE),
('AKRA', TRUE, FALSE, TRUE),
('AMMN', TRUE, FALSE, TRUE),
('AMRT', TRUE, FALSE, TRUE),
('ANTM', TRUE, FALSE, TRUE),
('ARTO', TRUE, FALSE, TRUE),
('ASII', TRUE, FALSE, TRUE),
('BBCA', TRUE, FALSE, TRUE),
('BBNI', TRUE, FALSE, TRUE),
('BBRI', TRUE, FALSE, TRUE),
('BBTN', TRUE, FALSE, TRUE),
('BMRI', TRUE, FALSE, TRUE),
('BRIS', TRUE, FALSE, TRUE),
('ADMR', TRUE, FALSE, TRUE),
('BRPT', TRUE, FALSE, TRUE),
('BUKA', TRUE, FALSE, TRUE),
('BYAN', TRUE, FALSE, TRUE),
('CPIN', TRUE, FALSE, TRUE),
('ESSA', TRUE, FALSE, TRUE),
('EXCL', TRUE, FALSE, TRUE),
('GOTO', TRUE, FALSE, TRUE),
('HRUM', TRUE, FALSE, TRUE),
('ICBP', TRUE, FALSE, TRUE),
('INCO', TRUE, FALSE, TRUE),
('INDF', TRUE, FALSE, TRUE),
('INKP', TRUE, FALSE, TRUE),
('INTP', TRUE, FALSE, TRUE),
('ISAT', TRUE, FALSE, TRUE),
('ITMG', TRUE, FALSE, TRUE),
('KLBF', TRUE, FALSE, TRUE),
('MAPI', TRUE, FALSE, TRUE),
('MDKA', TRUE, FALSE, TRUE),
('MEDC', TRUE, FALSE, TRUE),
('MIKA', TRUE, FALSE, TRUE),
('PGAS', TRUE, FALSE, TRUE),
('PGEO', TRUE, FALSE, TRUE),
('PTBA', TRUE, FALSE, TRUE),
('SIDO', TRUE, FALSE, TRUE),
('SMGR', TRUE, FALSE, TRUE),
('TBIG', TRUE, FALSE, TRUE),
('TINS', TRUE, FALSE, TRUE),
('TLKM', TRUE, FALSE, TRUE),
('TOWR', TRUE, FALSE, TRUE),
('UNTR', TRUE, FALSE, TRUE),
('UNVR', TRUE, FALSE, TRUE)
ON CONFLICT (ticker) DO NOTHING;
