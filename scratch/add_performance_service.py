import sys
import re

with open("services/paper_trading.py", "r") as f:
    content = f.read()

# Check if already exists
if "def get_performance_metrics" in content:
    print("Method already exists")
    sys.exit(0)

# We want to insert the method before the get_equity_history method
insertion_point = "def get_equity_history("

new_method = """def get_performance_metrics(self) -> dict:
        \"\"\"Calculate overall performance metrics for the current user.\"\"\"
        if not self.user_id:
            return {"status": "error", "message": "User ID is required"}

        wallet = self.session.query(PaperWallet).filter(PaperWallet.user_id == self.user_id).order_by(PaperWallet.id.asc()).first()
        if not wallet:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_profit": 0,
                "total_loss": 0,
                "avg_return_pct": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }

        trades = self.session.query(PaperTrade).filter(
            PaperTrade.wallet_id == wallet.id,
            PaperTrade.status.notin_(["OPEN", "PENDING_LIMIT", "PENDING_STOP", "CANCELLED"])
        ).all()

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_profit": 0,
                "total_loss": 0,
                "avg_return_pct": 0.0,
                "winning_trades": 0,
                "losing_trades": 0
            }

        winning_trades = 0
        losing_trades = 0
        total_profit = Decimal("0")
        total_loss = Decimal("0")
        total_return_pct = Decimal("0")

        for t in trades:
            pnl = t.realized_pnl or Decimal("0")
            pct = t.realized_pnl_pct or Decimal("0")
            total_return_pct += pct
            
            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
            elif pnl < 0:
                losing_trades += 1
                total_loss += abs(pnl)

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        profit_factor = float(total_profit) / float(total_loss) if total_loss > 0 else float(total_profit)
        avg_return = float(total_return_pct) / total_trades if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "win_rate_pct": float(win_rate),
            "profit_factor": profit_factor,
            "total_profit": float(total_profit),
            "total_loss": float(total_loss),
            "avg_return_pct": avg_return,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades
        }

    """

content = content.replace(insertion_point, new_method + insertion_point)

with open("services/paper_trading.py", "w") as f:
    f.write(content)

print("Method added to services/paper_trading.py")
