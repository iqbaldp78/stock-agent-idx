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
    signal           VARCHAR(10),
    entry_low        NUMERIC(12,2),
    entry_high       NUMERIC(12,2),
    max_entry        NUMERIC(12,2),
    target_1         NUMERIC(12,2),
    target_2         NUMERIC(12,2),
    stop_loss        NUMERIC(12,2),
    risk_reward      NUMERIC(5,2),
    conviction       VARCHAR(10),
    thesis           TEXT,
    entry_reasoning  TEXT,
    bandar_avg_7d    NUMERIC(12,2),
    bandar_avg_1m    NUMERIC(12,2),
    broker_utama     VARCHAR(100),
    time_horizon     VARCHAR(50),
    weight_mode      VARCHAR(20),
    composite_score  NUMERIC(4,2),
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
