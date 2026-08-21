"""
Script to remove erroneous trade ID 88 (TINS SL HIT) and recalculate wallet metrics.
"""

import sys
import os
from decimal import Decimal
from sqlalchemy import create_engine, text

# Database connection inside docker container or host pointing to container port
DB_URL = os.getenv("DATABASE_URL", "postgresql://stockuser:stockpassword@postgres:5432/stockagent")
engine = create_engine(DB_URL)

def run_fix():
    with engine.begin() as conn:
        # 1. Inspect trade 88 before deletion
        trade_88 = conn.execute(text("SELECT id, ticker, status, realized_pnl, wallet_id FROM paper_trades WHERE id = 88")).fetchone()
        if not trade_88:
            print("[fix_tins_sl_hit] Trade ID 88 not found. It may already be deleted.")
        else:
            print(f"[fix_tins_sl_hit] Found trade ID 88: {trade_88}")
            conn.execute(text("DELETE FROM paper_trades WHERE id = 88;"))
            print("[fix_tins_sl_hit] Deleted trade ID 88 successfully.")

        # 2. Fetch all remaining trades for wallet_id = 1
        trades = conn.execute(text("SELECT id, status, amount, fee, realized_pnl FROM paper_trades WHERE wallet_id = 1")).fetchall()

        topup = Decimal("100000000")
        total_invested = Decimal("0")
        total_pnl = Decimal("0")
        total_buy_cost = Decimal("0")
        total_net_sell = Decimal("0")

        for t in trades:
            tid, status, amount, fee, realized_pnl = t
            fee = fee or Decimal("0")
            realized_pnl = realized_pnl or Decimal("0")
            amount = amount or Decimal("0")

            if status in ["OPEN", "PENDING_LIMIT", "PENDING_STOP"]:
                total_invested += amount
                total_buy_cost += (amount + fee)
            elif status in ["CLOSED", "TP_HIT", "SL_HIT"]:
                total_pnl += realized_pnl
                total_buy_cost += (amount + fee)
                net_sell = amount + realized_pnl
                total_net_sell += net_sell
            elif status == "CANCELLED":
                pass

        cash = topup - total_buy_cost + total_net_sell

        print(f"[fix_tins_sl_hit] Recalculated values for wallet 1:")
        print(f"  Cash: {cash}")
        print(f"  Total Invested: {total_invested}")
        print(f"  Total Realized PnL: {total_pnl}")

        # 3. Update paper_wallet
        conn.execute(text("""
            UPDATE paper_wallet
            SET cash = :cash, total_invested = :invested, total_pnl = :pnl
            WHERE id = 1
        """), {"cash": cash, "invested": total_invested, "pnl": total_pnl})

        print("[fix_tins_sl_hit] paper_wallet ID 1 updated successfully.")

if __name__ == "__main__":
    run_fix()
