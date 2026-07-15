import sys
import os
from sqlalchemy import create_engine, text
from decimal import Decimal

engine = create_engine("postgresql://stockuser:stockpassword@localhost:5432/stockagent")

with engine.begin() as conn:
    # 1. DELETE ESSA trade
    conn.execute(text("DELETE FROM paper_trades WHERE ticker = 'ESSA' AND wallet_id = 1;"))
    print("Deleted ESSA trades.")

    # 2. DELETE AKRA pending trade (user_id IS NULL)
    conn.execute(text("DELETE FROM paper_trades WHERE ticker = 'AKRA' AND wallet_id = 1 AND status LIKE 'PENDING%';"))
    print("Deleted AKRA pending trades.")

    # 3. Fetch all remaining trades for wallet_id = 1
    result = conn.execute(text("SELECT status, amount, fee, realized_pnl FROM paper_trades WHERE wallet_id = 1"))
    trades = result.fetchall()

    total_invested = Decimal("0")
    total_pnl = Decimal("0")
    open_pending_cost = Decimal("0")
    closed_pnl_minus_fee = Decimal("0")

    for t in trades:
        status, amount, fee, realized_pnl = t
        if status in ["OPEN", "PENDING_LIMIT", "PENDING_STOP"]:
            total_invested += amount
            open_pending_cost += (amount + fee)
        elif status in ["TP_HIT", "SL_HIT", "CLOSED"]:
            total_pnl += realized_pnl
            closed_pnl_minus_fee += (realized_pnl - fee)
        # CANCELLED trades have net 0 effect on cash

    # Calculate Cash
    topup = Decimal("100000000")
    cash = topup - open_pending_cost + closed_pnl_minus_fee

    print(f"Calculated Cash: {cash}")
    print(f"Calculated Invested: {total_invested}")
    print(f"Calculated Total PNL: {total_pnl}")

    # 4. Update wallet_id = 1
    conn.execute(text("""
        UPDATE paper_wallet 
        SET cash = :cash, total_invested = :invested, total_pnl = :pnl 
        WHERE id = 1
    """), {"cash": cash, "invested": total_invested, "pnl": total_pnl})
    print("Wallet 1 updated successfully!")

