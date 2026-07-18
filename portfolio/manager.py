"""
Portfolio Manager
CRUD operations untuk portfolio holdings, avg cost calculator, P&L tracker.
"""
import logging
from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Session

from db import SessionLocal
from db.models import PortfolioHolding, DcaTransaction

logger = logging.getLogger(__name__)


# ============================================================
# Holdings CRUD
# ============================================================

def add_holding(
    ticker: str,
    total_shares: int,
    avg_cost: float,
    user_id: Optional[int] = None,
    notes: str = "",
) -> dict:
    """
    Tambah holding baru atau update jika sudah ada (upsert by ticker).
    total_shares: jumlah lembar saham (lot * 100)
    avg_cost: rata-rata harga beli per lembar
    """
    db: Session = SessionLocal()
    try:
        query = db.query(PortfolioHolding).filter_by(ticker=ticker.upper())
        if user_id:
            query = query.filter_by(user_id=user_id)
        existing = query.first()
        total_invested = float(total_shares) * float(avg_cost)

        if existing:
            existing.avg_cost = avg_cost
            existing.total_shares = total_shares
            existing.total_invested = total_invested
            existing.notes = notes or existing.notes
            existing.updated_at = datetime.now()
            db.commit()
            logger.info(f"[Portfolio] Updated holding: {ticker} {total_shares} lembar @ {avg_cost}")
            return _holding_to_dict(existing)
        else:
            holding = PortfolioHolding(
                ticker=ticker.upper(),
                avg_cost=avg_cost,
                total_shares=total_shares,
                total_invested=total_invested,
                status="ACTIVE",
                user_id=user_id,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(holding)
            db.commit()
            db.refresh(holding)
            logger.info(f"[Portfolio] Added holding: {ticker} {total_shares} lembar @ {avg_cost}")
            return _holding_to_dict(holding)
    except Exception as e:
        db.rollback()
        logger.error(f"[Portfolio] add_holding error: {e}")
        raise
    finally:
        db.close()


def get_all_holdings(user_id: Optional[int] = None) -> list:
    """Ambil semua active holdings."""
    db: Session = SessionLocal()
    try:
        query = db.query(PortfolioHolding).filter(PortfolioHolding.status == "ACTIVE")
        if user_id:
            query = query.filter(PortfolioHolding.user_id == user_id)
        
        holdings = (
            query
            .order_by(PortfolioHolding.ticker)
            .all()
        )
        return [_holding_to_dict(h) for h in holdings]
    finally:
        db.close()


def get_holding(ticker: str, user_id: Optional[int] = None) -> Optional[dict]:
    """Ambil satu holding by ticker."""
    db: Session = SessionLocal()
    try:
        query = db.query(PortfolioHolding).filter_by(ticker=ticker.upper())
        if user_id:
            query = query.filter_by(user_id=user_id)
        h = query.first()
        return _holding_to_dict(h) if h else None
    finally:
        db.close()


def delete_holding(ticker: str, user_id: Optional[int] = None) -> bool:
    """Soft delete: set status = CLOSED."""
    db: Session = SessionLocal()
    try:
        query = db.query(PortfolioHolding).filter_by(ticker=ticker.upper())
        if user_id:
            query = query.filter_by(user_id=user_id)
        h = query.first()
        if not h:
            return False
        h.status = "CLOSED"
        h.updated_at = datetime.now()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"[Portfolio] delete_holding error: {e}")
        return False
    finally:
        db.close()

def reset_all_holdings(user_id: Optional[int] = None) -> bool:
    """Reset all portfolio data including holdings, DCA transactions, and strategies."""
    try:
        with SessionLocal() as db:
            from db.models import PortfolioHolding, DcaTransaction, DcaStrategy
            # Depending on if DCA also uses user_id, we might need to filter.
            # But for holdings:
            query = db.query(PortfolioHolding)
            if user_id:
                query = query.filter(PortfolioHolding.user_id == user_id)
            query.delete()
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Error reset_all_holdings: {e}")
        return False

# ============================================================
# Calculator & Helpers
# ============================================================

def calculate_new_avg_cost(
    current_avg: float,
    current_shares: int,
    new_price: float,
    new_shares: int,
) -> float:
    """
    Hitung rata-rata harga beli baru setelah pembelian tambahan.
    Formula: (current_total + new_amount) / (current_shares + new_shares)
    """
    if current_shares <= 0:
        return float(new_price)
    current_total = float(current_avg) * float(current_shares)
    new_amount = float(new_price) * float(new_shares)
    total_shares = current_shares + new_shares
    return round((current_total + new_amount) / total_shares, 2)


def preview_avg_cost_after_buy(
    ticker: str,
    new_price: float,
    new_lots: int,
    user_id: Optional[int] = None,
) -> dict:
    """
    Preview avg cost baru jika melakukan pembelian.
    Berguna di UI sebelum user execute buy.
    new_lots: jumlah lot (1 lot = 100 lembar)
    """
    holding = get_holding(ticker, user_id=user_id)
    new_shares = new_lots * 100
    new_amount = new_price * new_shares

    if not holding:
        return {
            "ticker": ticker.upper(),
            "current_avg": None,
            "current_shares": 0,
            "current_lots": 0,
            "new_price": new_price,
            "new_lots": new_lots,
            "new_shares": new_shares,
            "new_amount": new_amount,
            "new_avg_cost": new_price,
            "total_shares_after": new_shares,
            "total_lots_after": new_lots,
        }

    current_avg = float(holding["avg_cost"])
    current_shares = int(holding["total_shares"])
    new_avg = calculate_new_avg_cost(current_avg, current_shares, new_price, new_shares)
    total_shares_after = current_shares + new_shares

    return {
        "ticker": ticker.upper(),
        "current_avg": current_avg,
        "current_shares": current_shares,
        "current_lots": current_shares // 100,
        "new_price": new_price,
        "new_lots": new_lots,
        "new_shares": new_shares,
        "new_amount": new_amount,
        "new_avg_cost": new_avg,
        "total_shares_after": total_shares_after,
        "total_lots_after": total_shares_after // 100,
    }


# ============================================================
# P&L & Price Updater
# ============================================================

def update_current_prices(holdings: list[dict]) -> list[dict]:
    """
    Update harga terkini untuk setiap holding dari fetcher.
    Returns holdings yang sudah di-update P&L-nya.
    """
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
    except ImportError:
        logger.warning("[Portfolio] fetcher_stockbit not available, skip price update")
        return holdings

    db: Session = SessionLocal()
    updated = []
    
    # Pre-load fetcher yfinance if needed
    try:
        from data.fetcher_yfinance import get_stock_info
    except ImportError:
        get_stock_info = None

    import concurrent.futures

    def _fetch_price_for_holding(h: dict) -> dict:
        ticker = h["ticker"].strip() # Bersihkan whitespace!
        current_price = 0.0
        try:
            # 1. Coba fetch dari Stockbit
            current_price = get_current_price_stockbit(ticker)
            
            # 2. Fallback fetch dari Yahoo Finance (jika gagal/0/None)
            if (not current_price or current_price <= 0) and get_stock_info:
                try:
                    info = get_stock_info(ticker)
                    current_price = info.get("current_price") or 0
                except Exception as yf_err:
                    logger.warning(f"[Portfolio] yfinance fallback failed for {ticker}: {yf_err}")

            if not current_price or current_price <= 0:
                current_price = float(h["avg_cost"]) # Fallback to avg_cost
        except Exception as e:
            logger.error(f"[Portfolio] Error update price for {ticker}: {e}")
            current_price = float(h["avg_cost"])

        h["current_price"] = current_price
        
        # Hitung P&L
        total_shares = int(h["total_shares"])
        avg_cost = float(h["avg_cost"])
        
        market_value = current_price * total_shares
        total_cost = avg_cost * total_shares
        
        unrealized_pnl = market_value - total_cost
        unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        h["market_value"] = market_value
        h["total_cost"] = total_cost
        h["unrealized_pnl"] = unrealized_pnl
        h["unrealized_pnl_pct"] = unrealized_pnl_pct
        return h

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            updated = list(executor.map(_fetch_price_for_holding, holdings))
        
        db: Session = SessionLocal()
        for h in updated:
            try:
                # Update DB
                holding_obj = db.query(PortfolioHolding).filter_by(ticker=h["ticker"]).first()
                if holding_obj:
                    holding_obj.current_price = h["current_price"]
                    holding_obj.current_value = h["market_value"]
                    holding_obj.unrealized_pnl = h["unrealized_pnl"]
                    holding_obj.unrealized_pnl_pct = round(h["unrealized_pnl_pct"], 2)
                    holding_obj.updated_at = datetime.now()
            except Exception as e:
                logger.warning(f"[Portfolio] price update error for {h['ticker']}: {e}")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Portfolio] update_current_prices error: {e}")
    finally:
        db.close()

    return updated


def get_portfolio_summary(holdings: list[dict]) -> dict:
    """
    Hitung summary portfolio: total invested, current value, total P&L.
    """
    total_invested = sum(
        float(h.get("avg_cost", 0)) * int(h.get("total_shares", 0))
        for h in holdings
    )
    total_current_value = sum(
        float(h.get("current_value") or 0)
        for h in holdings
    )
    total_pnl = total_current_value - total_invested if total_current_value > 0 else 0
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    # Best & worst performer
    performers = [
        h for h in holdings
        if h.get("unrealized_pnl_pct") is not None
    ]
    best = max(performers, key=lambda x: float(x.get("unrealized_pnl_pct") or 0), default=None)
    worst = min(performers, key=lambda x: float(x.get("unrealized_pnl_pct") or 0), default=None)

    return {
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 2),
        "best_performer": best["ticker"] if best else None,
        "best_pnl_pct": float(best.get("unrealized_pnl_pct") or 0) if best else None,
        "worst_performer": worst["ticker"] if worst else None,
        "worst_pnl_pct": float(worst.get("unrealized_pnl_pct") or 0) if worst else None,
        "holdings_count": len(holdings),
    }


# ============================================================
# Transaction Recording
# ============================================================

def record_buy(
    ticker: str,
    lots: int,
    price: float,
    broker_fee: float = 0.0,
    transaction_date: Optional[date] = None,
    signal_id: Optional[int] = None,
    user_id: Optional[int] = None,
    notes: str = "",
) -> dict:
    """
    Record transaksi beli dan update holding avg cost.
    lots: jumlah lot (1 lot = 100 lembar)
    """
    shares = lots * 100
    amount = price * shares
    txn_date = transaction_date or datetime.now()

    db: Session = SessionLocal()
    try:
        # Get or create holding
        query = db.query(PortfolioHolding).filter_by(ticker=ticker.upper())
        if user_id:
            query = query.filter_by(user_id=user_id)
        holding = query.first()

        if holding:
            new_avg = calculate_new_avg_cost(
                float(holding.avg_cost),
                int(holding.total_shares),
                price,
                shares,
            )
            holding.avg_cost = new_avg
            holding.total_shares = int(holding.total_shares) + shares
            holding.total_invested = float(holding.total_invested or 0) + amount
            holding.updated_at = datetime.now()
            holding_id = holding.id
        else:
            holding = PortfolioHolding(
                ticker=ticker.upper(),
                avg_cost=price,
                total_shares=shares,
                total_invested=amount,
                status="ACTIVE",
                user_id=user_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db.add(holding)
            db.flush()
            holding_id = holding.id

        # Record transaction
        txn = DcaTransaction(
            holding_id=holding_id,
            ticker=ticker.upper(),
            transaction_type="BUY",
            shares=shares,
            price=price,
            amount=amount,
            broker_fee=broker_fee,
            transaction_date=txn_date,
            signal_id=signal_id,
            notes=notes,
            created_at=datetime.now(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        logger.info(f"[Portfolio] BUY recorded: {ticker} {lots} lot @ {price}")
        return {
            "ticker": ticker.upper(),
            "transaction_id": txn.id,
            "lots": lots,
            "shares": shares,
            "price": price,
            "amount": amount,
            "new_avg_cost": float(holding.avg_cost),
            "total_shares": int(holding.total_shares),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[Portfolio] record_buy error: {e}")
        raise
    finally:
        db.close()


def record_sell(
    ticker: str,
    lots: int,
    price: float,
    broker_fee: float = 0.0,
    transaction_date: Optional[date] = None,
    user_id: Optional[int] = None,
    notes: str = "",
) -> dict:
    """
    Record transaksi jual dan update holding shares.
    """
    shares = lots * 100
    amount = price * shares
    txn_date = transaction_date or datetime.now()

    db: Session = SessionLocal()
    try:
        query = db.query(PortfolioHolding).filter_by(ticker=ticker.upper())
        if user_id:
            query = query.filter_by(user_id=user_id)
        holding = query.first()
        if not holding:
            raise ValueError(f"Holding {ticker} tidak ditemukan")

        if int(holding.total_shares) < shares:
            raise ValueError(f"Shares tidak cukup: punya {holding.total_shares}, jual {shares}")

        holding.total_shares = int(holding.total_shares) - shares
        if holding.total_shares == 0:
            holding.status = "CLOSED"
        holding.updated_at = datetime.now()

        txn = DcaTransaction(
            holding_id=holding.id,
            ticker=ticker.upper(),
            transaction_type="SELL",
            shares=shares,
            price=price,
            amount=amount,
            broker_fee=broker_fee,
            transaction_date=txn_date,
            notes=notes,
            created_at=datetime.now(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        logger.info(f"[Portfolio] SELL recorded: {ticker} {lots} lot @ {price}")
        return {
            "ticker": ticker.upper(),
            "transaction_id": txn.id,
            "lots": lots,
            "shares": shares,
            "price": price,
            "amount": amount,
            "remaining_shares": int(holding.total_shares),
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[Portfolio] record_sell error: {e}")
        raise
    finally:
        db.close()


def get_transactions(
    ticker: Optional[str] = None,
    txn_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
) -> list[dict]:
    """Ambil history transaksi dengan filter opsional."""
    db: Session = SessionLocal()
    try:
        q = db.query(DcaTransaction)
        if user_id is not None:
            from db.models import PortfolioHolding
            q = q.join(PortfolioHolding, DcaTransaction.holding_id == PortfolioHolding.id).filter(PortfolioHolding.user_id == user_id)
        if ticker:
            q = q.filter(DcaTransaction.ticker == ticker.upper())
        if txn_type:
            q = q.filter(DcaTransaction.transaction_type == txn_type.upper())
        if start_date:
            q = q.filter(DcaTransaction.transaction_date >= start_date)
        if end_date:
            q = q.filter(DcaTransaction.transaction_date <= end_date)
        q = q.order_by(DcaTransaction.transaction_date.desc())
        return [_txn_to_dict(t) for t in q.all()]
    finally:
        db.close()


# ============================================================
# DCA Level Generator
# ============================================================

def calculate_dca_levels(
    entry_low: float,
    entry_high: float,
    max_entry: float,
    total_budget: float,
    dca_count: int = 3,
) -> dict:
    """
    Generate DCA entry levels dari entry zone.

    Logic:
    - dca_count levels merata antara entry_low dan max_entry
    - Budget dibagi sama rata per level
    - Shares dihitung dari amount per level / price per level

    Returns:
    {
        "levels": [{"level": 1, "price": x, "amount": y, "lots": z, "shares": w}, ...],
        "amount_per_level": float,
        "total_budget": float,
        "entry_low": float,
        "max_entry": float,
    }
    """
    if dca_count < 2:
        dca_count = 2
    if dca_count > 5:
        dca_count = 5

    # Generate price levels merata dari entry_low ke max_entry
    if dca_count == 1:
        prices = [entry_low]
    elif dca_count == 2:
        prices = [entry_low, max_entry]
    elif dca_count == 3:
        prices = [entry_low, entry_high, max_entry]
    else:
        # Interpolasi merata
        step = (max_entry - entry_low) / (dca_count - 1)
        prices = [round(entry_low + step * i, 0) for i in range(dca_count)]

    total_weight = sum(range(1, dca_count + 1))
    levels = []
    for i, price in enumerate(prices):
        weight = i + 1
        amount_budget = (weight / total_weight) * total_budget
        shares = int(amount_budget / price)
        # Round down ke kelipatan 100 (1 lot)
        shares = (shares // 100) * 100
        lots = shares // 100
        actual_amount = shares * price if shares > 0 else 0
        levels.append({
            "level": i + 1,
            "price": round(price, 0),
            "amount_budget": round(amount_budget, 0),
            "actual_amount": round(actual_amount, 0),
            "lots": lots,
            "shares": shares,
        })

    return {
        "levels": levels,
        "amount_per_level": round(total_budget / dca_count, 0) if dca_count > 0 else 0,
        "total_budget": total_budget,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "max_entry": max_entry,
        "dca_count": dca_count,
    }


# ============================================================
# Helpers
# ============================================================

def _holding_to_dict(h: PortfolioHolding) -> dict:
    return {
        "id": h.id,
        "ticker": h.ticker,
        "avg_cost": float(h.avg_cost) if h.avg_cost else 0,
        "total_shares": int(h.total_shares) if h.total_shares else 0,
        "total_lots": (int(h.total_shares) // 100) if h.total_shares else 0,
        "total_invested": float(h.total_invested) if h.total_invested else 0,
        "current_price": float(h.current_price) if h.current_price else None,
        "current_value": float(h.current_value) if h.current_value else None,
        "unrealized_pnl": float(h.unrealized_pnl) if h.unrealized_pnl else None,
        "unrealized_pnl_pct": float(h.unrealized_pnl_pct) if h.unrealized_pnl_pct else None,
        "status": h.status,
        "notes": h.notes or "",
        "created_at": str(h.created_at) if h.created_at else None,
        "updated_at": str(h.updated_at) if h.updated_at else None,
    }


def _txn_to_dict(t: DcaTransaction) -> dict:
    return {
        "id": t.id,
        "holding_id": t.holding_id,
        "ticker": t.ticker,
        "transaction_type": t.transaction_type,
        "shares": int(t.shares) if t.shares else 0,
        "lots": (int(t.shares) // 100) if t.shares else 0,
        "price": float(t.price) if t.price else 0,
        "amount": float(t.amount) if t.amount else 0,
        "broker_fee": float(t.broker_fee) if t.broker_fee else 0,
        "transaction_date": str(t.transaction_date) if t.transaction_date else None,
        "signal_id": t.signal_id,
        "notes": t.notes or "",
        "created_at": str(t.created_at) if t.created_at else None,
    }
