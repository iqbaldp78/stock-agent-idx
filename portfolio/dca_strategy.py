"""
DCA Strategy Module
Logic DCA: create strategy dari signal, check triggers, timing recommendation.
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from db import SessionLocal
from db.models import DcaStrategy, Signal
from portfolio.manager import calculate_dca_levels, record_buy, _holding_to_dict

logger = logging.getLogger(__name__)


# ============================================================
# Create DCA Strategy
# ============================================================

def create_dca_from_signal(
    signal_id: int,
    total_budget: float,
    dca_count: int = 3,
) -> dict:
    """
    Buat DCA strategy dari TOP PICK signal.
    Entry zones (entry_low, entry_high, max_entry) diambil dari signal.
    """
    db: Session = SessionLocal()
    try:
        signal = db.query(Signal).filter_by(id=signal_id).first()
        if not signal:
            raise ValueError(f"Signal ID {signal_id} tidak ditemukan")

        entry_low = float(signal.entry_low or 0)
        entry_high = float(signal.entry_high or 0)
        max_entry = float(signal.max_entry or 0)

        if not entry_low or not max_entry:
            raise ValueError(f"Signal {signal_id} tidak punya entry zone yang valid")

        if not entry_high:
            entry_high = (entry_low + max_entry) / 2

        levels_data = calculate_dca_levels(
            entry_low=entry_low,
            entry_high=entry_high,
            max_entry=max_entry,
            total_budget=total_budget,
            dca_count=dca_count,
        )

        # next_buy_price = level terendah (harga terbaik)
        next_buy_price = levels_data["levels"][0]["price"] if levels_data["levels"] else entry_low

        strategy = DcaStrategy(
            ticker=signal.ticker,
            total_budget=total_budget,
            remaining_budget=total_budget,
            dca_count=dca_count,
            entry_low=entry_low,
            entry_high=entry_high,
            max_entry=max_entry,
            next_buy_price=next_buy_price,
            signal_id=signal_id,
            tp1=float(signal.target_1) if signal.target_1 else None,
            tp2=float(signal.target_2) if signal.target_2 else None,
            tp3=float(signal.target_3) if signal.target_3 else None,
            stop_loss=float(signal.stop_loss) if signal.stop_loss else None,
            status="ACTIVE",
            activated_at=date.today(),
            created_at=date.today(),
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)

        logger.info(f"[DCA] Created strategy: {signal.ticker} budget={total_budget} levels={dca_count}")
        return {
            **_strategy_to_dict(strategy),
            "levels": levels_data["levels"],
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[DCA] create_dca_from_signal error: {e}")
        raise
    finally:
        db.close()


def create_dca_manual(
    ticker: str,
    total_budget: float,
    entry_low: float,
    entry_high: float,
    max_entry: float,
    dca_count: int = 3,
    tp1: Optional[float] = None,
    tp2: Optional[float] = None,
    tp3: Optional[float] = None,
    stop_loss: Optional[float] = None,
) -> dict:
    """Buat DCA strategy secara manual tanpa signal."""
    if not entry_high:
        entry_high = (entry_low + max_entry) / 2

    levels_data = calculate_dca_levels(
        entry_low=entry_low,
        entry_high=entry_high,
        max_entry=max_entry,
        total_budget=total_budget,
        dca_count=dca_count,
    )

    db: Session = SessionLocal()
    try:
        strategy = DcaStrategy(
            ticker=ticker.upper(),
            total_budget=total_budget,
            remaining_budget=total_budget,
            dca_count=dca_count,
            entry_low=entry_low,
            entry_high=entry_high,
            max_entry=max_entry,
            next_buy_price=levels_data["levels"][0]["price"] if levels_data["levels"] else entry_low,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            stop_loss=stop_loss,
            status="ACTIVE",
            activated_at=date.today(),
            created_at=date.today(),
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)

        logger.info(f"[DCA] Created manual strategy: {ticker} budget={total_budget}")
        return {
            **_strategy_to_dict(strategy),
            "levels": levels_data["levels"],
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[DCA] create_dca_manual error: {e}")
        raise
    finally:
        db.close()


# ============================================================
# Get / List Strategies
# ============================================================

def get_active_strategies() -> list[dict]:
    """Ambil semua DCA strategies yang masih ACTIVE."""
    db: Session = SessionLocal()
    try:
        strategies = (
            db.query(DcaStrategy)
            .filter(DcaStrategy.status == "ACTIVE")
            .order_by(DcaStrategy.created_at.desc())
            .all()
        )
        return [_strategy_to_dict(s) for s in strategies]
    finally:
        db.close()


def get_all_strategies() -> list[dict]:
    """Ambil semua DCA strategies."""
    db: Session = SessionLocal()
    try:
        strategies = (
            db.query(DcaStrategy)
            .order_by(DcaStrategy.created_at.desc())
            .all()
        )
        return [_strategy_to_dict(s) for s in strategies]
    finally:
        db.close()


def get_strategy_with_levels(strategy_id: int) -> Optional[dict]:
    """Ambil strategy + regenerate levels dari entry zone."""
    db: Session = SessionLocal()
    try:
        s = db.query(DcaStrategy).filter_by(id=strategy_id).first()
        if not s:
            return None
        result = _strategy_to_dict(s)
        if s.entry_low and s.max_entry:
            levels_data = calculate_dca_levels(
                entry_low=float(s.entry_low),
                entry_high=float(s.entry_high or (float(s.entry_low) + float(s.max_entry)) / 2),
                max_entry=float(s.max_entry),
                total_budget=float(s.remaining_budget or s.total_budget),
                dca_count=int(s.dca_count or 3),
            )
            result["levels"] = levels_data["levels"]
        return result
    finally:
        db.close()


def deactivate_strategy(strategy_id: int) -> bool:
    """Set strategy ke CANCELLED."""
    db: Session = SessionLocal()
    try:
        s = db.query(DcaStrategy).filter_by(id=strategy_id).first()
        if not s:
            return False
        s.status = "CANCELLED"
        s.completed_at = date.today()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"[DCA] deactivate_strategy error: {e}")
        return False
    finally:
        db.close()


# ============================================================
# Trigger Check
# ============================================================

def check_dca_triggers(current_price: float, strategy_id: int) -> dict:
    """
    Cek apakah current price menyentuh next_buy_price dari DCA strategy.
    Returns: {"triggered": bool, "level": int, "price": float, "action": str}
    """
    db: Session = SessionLocal()
    try:
        s = db.query(DcaStrategy).filter_by(id=strategy_id, status="ACTIVE").first()
        if not s:
            return {"triggered": False}

        next_buy = float(s.next_buy_price or 0)
        if not next_buy:
            return {"triggered": False}

        # Triggered jika current price <= next_buy_price (harga turun ke target DCA)
        triggered = current_price <= next_buy

        return {
            "strategy_id": strategy_id,
            "ticker": s.ticker,
            "triggered": triggered,
            "current_price": current_price,
            "next_buy_price": next_buy,
            "distance_pct": round((current_price - next_buy) / next_buy * 100, 2) if next_buy else None,
            "remaining_budget": float(s.remaining_budget or 0),
        }
    finally:
        db.close()


def check_all_dca_triggers() -> list[dict]:
    """
    Check semua active strategies untuk current price triggers.
    Digunakan oleh scheduler harian.
    """
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
    except ImportError:
        logger.warning("[DCA] fetcher_stockbit not available")
        return []

    strategies = get_active_strategies()
    results = []
    for s in strategies:
        try:
            current_price = get_current_price_stockbit(s["ticker"])
            if not current_price:
                continue
            trigger = check_dca_triggers(current_price, s["id"])
            if trigger.get("triggered"):
                results.append(trigger)
        except Exception as e:
            logger.warning(f"[DCA] check trigger error for {s['ticker']}: {e}")
    return results


# ============================================================
# Timing Recommendation
# ============================================================

def recommend_dca_timing(ticker: str) -> dict:
    """
    Rekomendasi timing DCA berdasarkan true cost bandar dari signals table.

    Status:
    - IDEAL: current price <= true_cost_1m (harga di bawah bandar)
    - ACCEPTABLE: 0-2% di atas true cost
    - CAUTION: 2-5% di atas true cost
    - AVOID: >5% di atas true cost
    """
    try:
        from data.fetcher_stockbit import get_current_price_stockbit
        current_price = get_current_price_stockbit(ticker)
    except Exception:
        current_price = None

    # Ambil sinyal terbaru untuk ticker ini
    db: Session = SessionLocal()
    try:
        latest_signal = (
            db.query(Signal)
            .filter(Signal.ticker == ticker.upper())
            .order_by(Signal.run_date.desc())
            .first()
        )

        bandar_1m = float(latest_signal.bandar_avg_1m) if latest_signal and latest_signal.bandar_avg_1m else None
        bandar_7d = float(latest_signal.bandar_avg_7d) if latest_signal and latest_signal.bandar_avg_7d else None
        signal_date = str(latest_signal.run_date) if latest_signal else None

        # True cost bandar untuk timing reference
        true_cost = bandar_1m or bandar_7d

        if not current_price or not true_cost:
            return {
                "ticker": ticker.upper(),
                "status": "NO_DATA",
                "current_price": current_price,
                "true_cost_1m": bandar_1m,
                "true_cost_7d": bandar_7d,
                "distance_pct": None,
                "recommended_buy": true_cost,
                "reason": "Data harga atau true cost bandar tidak tersedia",
                "signal_date": signal_date,
            }

        distance_pct = (current_price - true_cost) / true_cost * 100

        if distance_pct <= 0:
            status = "IDEAL"
            reason = f"Harga {current_price:,.0f} masih di bawah true cost bandar 1M ({true_cost:,.0f}). Timing terbaik untuk beli."
            recommended_buy = current_price
        elif distance_pct <= 2:
            status = "ACCEPTABLE"
            reason = f"Harga {distance_pct:.1f}% di atas true cost bandar 1M. Masih acceptable untuk DCA."
            recommended_buy = true_cost
        elif distance_pct <= 5:
            status = "CAUTION"
            reason = f"Harga {distance_pct:.1f}% di atas true cost bandar 1M. Sebaiknya tunggu koreksi dulu."
            recommended_buy = round(true_cost * 1.01, 0)
        else:
            status = "AVOID"
            reason = f"Harga {distance_pct:.1f}% di atas true cost bandar 1M ({true_cost:,.0f}). Hindari entry sekarang."
            recommended_buy = round(true_cost, 0)

        return {
            "ticker": ticker.upper(),
            "status": status,
            "current_price": current_price,
            "true_cost_1m": bandar_1m,
            "true_cost_7d": bandar_7d,
            "distance_pct": round(distance_pct, 2),
            "recommended_buy": recommended_buy,
            "reason": reason,
            "signal_date": signal_date,
        }
    finally:
        db.close()


# ============================================================
# Helpers
# ============================================================

def _strategy_to_dict(s: DcaStrategy) -> dict:
    total_budget = float(s.total_budget) if s.total_budget else 0
    remaining = float(s.remaining_budget) if s.remaining_budget else total_budget
    used = total_budget - remaining
    used_pct = (used / total_budget * 100) if total_budget > 0 else 0

    return {
        "id": s.id,
        "ticker": s.ticker,
        "holding_id": s.holding_id,
        "total_budget": total_budget,
        "remaining_budget": remaining,
        "used_budget": used,
        "used_budget_pct": round(used_pct, 1),
        "dca_count": int(s.dca_count or 3),
        "entry_low": float(s.entry_low) if s.entry_low else None,
        "entry_high": float(s.entry_high) if s.entry_high else None,
        "max_entry": float(s.max_entry) if s.max_entry else None,
        "next_buy_price": float(s.next_buy_price) if s.next_buy_price else None,
        "signal_id": s.signal_id,
        "tp1": float(s.tp1) if s.tp1 else None,
        "tp2": float(s.tp2) if s.tp2 else None,
        "tp3": float(s.tp3) if s.tp3 else None,
        "stop_loss": float(s.stop_loss) if s.stop_loss else None,
        "status": s.status,
        "activated_at": str(s.activated_at) if s.activated_at else None,
        "completed_at": str(s.completed_at) if s.completed_at else None,
        "created_at": str(s.created_at) if s.created_at else None,
    }
