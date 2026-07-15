-- 1. DELETE ESSA trade
DELETE FROM paper_trades WHERE ticker = 'ESSA' AND wallet_id = 1;

-- 2. DELETE AKRA pending trade
DELETE FROM paper_trades WHERE ticker = 'AKRA' AND wallet_id = 1 AND status LIKE 'PENDING%';

-- 3. Calculate and update wallet_id = 1
WITH aggregated AS (
    SELECT 
        SUM(CASE WHEN status IN ('OPEN', 'PENDING_LIMIT', 'PENDING_STOP') THEN amount ELSE 0 END) as total_invested,
        SUM(CASE WHEN status IN ('OPEN', 'PENDING_LIMIT', 'PENDING_STOP') THEN amount + fee ELSE 0 END) as open_pending_cost,
        SUM(CASE WHEN status IN ('TP_HIT', 'SL_HIT', 'CLOSED') THEN realized_pnl ELSE 0 END) as total_pnl,
        SUM(CASE WHEN status IN ('TP_HIT', 'SL_HIT', 'CLOSED') THEN realized_pnl - fee ELSE 0 END) as closed_pnl_minus_fee
    FROM paper_trades 
    WHERE wallet_id = 1
)
UPDATE paper_wallet
SET 
    cash = 100000000 - aggregated.open_pending_cost + aggregated.closed_pnl_minus_fee,
    total_invested = aggregated.total_invested,
    total_pnl = aggregated.total_pnl
FROM aggregated
WHERE paper_wallet.id = 1;

SELECT cash, total_invested, total_pnl FROM paper_wallet WHERE id = 1;
