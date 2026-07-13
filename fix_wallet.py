from db import SessionLocal
from db.models import PaperTrade, PaperWallet
from decimal import Decimal

db = SessionLocal()
wallet = db.query(PaperWallet).order_by(PaperWallet.id.asc()).first()

if wallet:
    # Delete duplicate wallets
    duplicates = db.query(PaperWallet).filter(PaperWallet.id > wallet.id).all()
    if duplicates:
        print(f"Moving trades from {len(duplicates)} duplicate wallets to primary wallet ID {wallet.id}...")
        dup_ids = [d.id for d in duplicates]
        db.query(PaperTrade).filter(PaperTrade.wallet_id.in_(dup_ids)).update({PaperTrade.wallet_id: wallet.id}, synchronize_session=False)
        db.commit()
        print(f"Deleting {len(duplicates)} duplicate wallets...")
        for dup in duplicates:
            db.delete(dup)
        db.commit()

    active_trades = db.query(PaperTrade).filter(PaperTrade.status.in_(["OPEN", "PENDING_LIMIT", "PENDING_STOP"])).all()
    actual_invested = sum([t.amount for t in active_trades])
    
    closed_trades = db.query(PaperTrade).filter(PaperTrade.status.not_in(["OPEN", "PENDING_LIMIT", "PENDING_STOP", "CANCELLED"])).all()
    
    total_realized_pnl = sum([t.realized_pnl for t in closed_trades if t.realized_pnl is not None])
    
    expected_cash = wallet.total_topup
    for t in active_trades:
        expected_cash -= (t.amount + t.fee)
        
    for t in closed_trades:
        expected_cash += (t.realized_pnl - t.fee)
        
    print(f"Current wallet cash: {wallet.cash}")
    print(f"Recalculated cash: {expected_cash}")
    print(f"Current wallet invested: {wallet.total_invested}")
    print(f"Recalculated invested: {actual_invested}")
    
    wallet.cash = expected_cash
    wallet.total_invested = actual_invested
    wallet.total_pnl = total_realized_pnl
    
    db.commit()
    print("Wallet has been fully synced based on trade history.")
else:
    print("No wallet found.")

db.close()
