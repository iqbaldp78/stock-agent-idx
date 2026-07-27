"""
DB — Tracker
Menyimpan hasil analisis ke PostgreSQL.
"""
import json
import logging
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import SessionLocal
from db.models import AgentScore, DebateLog, Signal

logger = logging.getLogger(__name__)


def save_scores(run_date: datetime, scores: dict, composites: dict,
                macro_data: dict) -> None:
    """Simpan scoring hasil agent ke tabel agent_scores."""
    db: Session = SessionLocal()
    try:
        for ticker, composite in composites.items():
            ticker_scores = scores.get(ticker, {})
            bandarm = ticker_scores.get("bandarm", {})
            tech = ticker_scores.get("technical", {})
            fund = ticker_scores.get("fundamental", {})

            record = AgentScore(
                run_date=run_date,  # already datetime
                ticker=ticker,
                fundamental_score=fund.get("score"),
                technical_score=tech.get("score"),
                bandarm_score=bandarm.get("score"),
                macro_signal=macro_data.get("ihsg_trend", "UNKNOWN"),
                composite_score=composite["composite_score"],
                weight_mode=composite["weight_mode"],
                weights_used=json.dumps(composite["weights_used"]),
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def save_debate_log(run_date: datetime, debate_log: list) -> None:
    """Simpan log debat ke tabel debate_logs."""
    db: Session = SessionLocal()
    try:
        for entry in debate_log:
            record = DebateLog(
                run_date=run_date,  # already datetime
                ticker=entry["ticker"],
                round=entry["round"],
                agent=entry["agent"],
                argument=entry["argument"],
                vote=entry["vote"],
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def save_signals(run_date: datetime, top_picks: list, scores: dict, batch_id: str | None = None, is_konglo: bool = False) -> None:
    """Simpan final signals ke tabel signals. Jika data untuk (ticker, run_date, is_konglo) sudah ada, abaikan (jangan insert duplikat)."""
    db: Session = SessionLocal()
    try:
        # Konversi run_date ke DATE supaya gampang dicek
        run_date_only = run_date.date() if isinstance(run_date, datetime) else run_date
        
        for pick in top_picks:
            ticker = pick["ticker"]
            
            # Cek apakah sudah ada record dengan ticker dan tanggal yang sama
            existing_signal = db.query(Signal).filter(
                Signal.ticker == ticker,
                func.date(Signal.run_date) == run_date_only,
                Signal.is_konglo == is_konglo
            ).first()
            
            if existing_signal:
                logger.info(f"Skipping insert for {ticker} on {run_date_only} (is_konglo={is_konglo}): already exists.")
                continue
                
            ticker_scores = scores.get(ticker, {})
            bandarm = ticker_scores.get("bandarm", {})
            price_analysis = bandarm.get("price_analysis", {})
            decision_label = str(pick.get("decision_label") or "BUY").upper()
            db_signal = "BUY" if decision_label in ("STRONG BUY", "BUY", "SPEC BUY") else decision_label

            # Parse entry zone
            entry_zone = pick.get("entry_zone", "")
            entry_low = None
            entry_high = None
            separator = "–" if "–" in str(entry_zone) else "-"
            if separator in str(entry_zone):
                parts = str(entry_zone).split(separator)
                try:
                    entry_low = _parse_number(parts[0])
                    entry_high = _parse_number(parts[1])
                except (ValueError, IndexError):
                    pass

            record = Signal(
                run_date=run_date,  # already datetime
                ticker=ticker,
                rank=pick.get("rank"),
                signal=db_signal,
                entry_low=entry_low,
                entry_high=entry_high,
                max_entry=_parse_number(pick.get("max_entry")),
                target_1=_parse_number(pick.get("target_1")),
                target_2=_parse_number(pick.get("target_2")),
                target_3=_parse_number(pick.get("target_3")),
                stop_loss=_parse_number(pick.get("stop_loss")),
                risk_reward=_parse_risk_reward(pick.get("risk_reward")),
                conviction=pick.get("conviction"),
                thesis=pick.get("thesis") or (
                    f"{pick.get('bandarm_signal', '')} — composite {pick.get('composite_score', '')}"
                    f" — decision {decision_label} — pred {pick.get('pred_return', 0)}%"
                ),
                entry_reasoning=pick.get("entry_reasoning") or "Entry berdasarkan avg cost bandar",
                bandar_avg_7d=price_analysis.get("bandar_avg_7d"),
                bandar_avg_1m=price_analysis.get("bandar_avg_1m"),
                broker_utama=", ".join(pick.get("broker_to_watch", [])),
                time_horizon=pick.get("time_horizon") or "Positional (4-6 minggu)",
                weight_mode=pick.get("weight_mode"),
                composite_score=pick.get("composite_score"),
                ml_prediction=pick.get("ml_prediction"),
                price_prediction=pick.get("price_prediction"),
                broker_true_costs=pick.get("broker_true_costs"),
                broker_distributors=pick.get("broker_distributors"),
                fair_value=pick.get("fair_value"),
                batch_id=batch_id,
                is_konglo=is_konglo,
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def save_full_result(result: dict, batch_id: str | None = None, is_konglo: bool = False) -> None:
    """Simpan semua hasil analisis sekaligus."""
    today = datetime.now()
    batch_id = batch_id or str(uuid.uuid4())

    if result.get("composites"):
        save_scores(today, result["scores"], result["composites"], result["macro_data"])

    if result.get("debate_log"):
        save_debate_log(today, result["debate_log"])

    top_picks = result.get("top_picks") or []
    top_tickers = {p["ticker"] for p in top_picks}
    all_signals = list(top_picks)

    if result.get("composites"):
        for ticker, comp in result["composites"].items():
            if ticker not in top_tickers:
                all_signals.append({
                    "ticker": ticker,
                    "rank": None,
                    "decision_label": "AVOID",
                    "composite_score": comp.get("composite_score", 0),
                    "weight_mode": comp.get("weight_mode", ""),
                    "conviction": "LOW",
                    "thesis": "Tidak masuk kriteria Top Picks (Evaluated by system)."
                })

    if all_signals:
        save_signals(today, all_signals, result.get("scores", {}), batch_id=batch_id, is_konglo=is_konglo)

    if result.get("ihsg_prediction"):
        save_ihsg_prediction(today, result["ihsg_prediction"], batch_id=batch_id)
def _truncate(value, max_len: int) -> str | None:
    """Truncate string agar tidak overflow kolom VARCHAR."""
    if value is None:
        return None
    return str(value)[:max_len]


def _parse_risk_reward(value) -> float | None:
    """Parse risk_reward dari format '1:X.X' atau float ke float ratio."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if ":" in s:
        parts = s.split(":")
        try:
            return float(parts[-1])
        except (ValueError, IndexError):
            return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_number(value) -> float | None:
    """Parse number ke float. Handles plain float/int dan string format Indonesia."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    # Format Indonesia: titik sebagai ribuan, koma sebagai desimal (e.g. "1.234,56")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Koma bisa sebagai ribuan ("1,234") atau desimal ("1,5") — cek posisinya
        comma_pos = s.rfind(",")
        if len(s) - comma_pos - 1 <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    # Titik saja: ribuan separator ("1.234") atau desimal ("1.5")
    elif s.count(".") == 1:
        dot_pos = s.rfind(".")
        if len(s) - dot_pos - 1 == 3 and dot_pos > 0:
            s = s.replace(".", "")
        # else: titik adalah desimal, biarkan
    else:
        s = s.replace(".", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def save_ihsg_prediction(run_date: datetime, ihsg_pred: dict, batch_id: str | None = None) -> None:
    """Simpan IHSG prediction ke tabel ihsg_predictions."""
    if not ihsg_pred or not ihsg_pred.get("current_price"):
        return

    from sqlalchemy import text
    db: Session = SessionLocal()
    try:
        sql = """
            INSERT INTO ihsg_predictions
            (run_date, current_price, confidence, direction, volatility_level,
             day_1_price, day_1_pct, day_3_price, day_3_pct, day_5_price, day_5_pct,
             day_7_price, day_7_pct, reasoning, key_drivers, risks, component_scores,
             ihsg_trend, macro_signal)
            VALUES (:run_date, :current_price, :confidence, :direction, :volatility_level,
                    :day_1_price, :day_1_pct, :day_3_price, :day_3_pct, :day_5_price, :day_5_pct,
                    :day_7_price, :day_7_pct, :reasoning, :key_drivers, :risks, :component_scores,
                    :ihsg_trend, :macro_signal)
        """
        db.execute(text(sql), {
            "run_date": run_date,
            "current_price": ihsg_pred.get("current_price"),
            "confidence": ihsg_pred.get("confidence"),
            "direction": ihsg_pred.get("direction"),
            "volatility_level": ihsg_pred.get("volatility_level"),
            "day_1_price": ihsg_pred.get("day_1_price"),
            "day_1_pct": ihsg_pred.get("day_1_pct"),
            "day_3_price": ihsg_pred.get("day_3_price"),
            "day_3_pct": ihsg_pred.get("day_3_pct"),
            "day_5_price": ihsg_pred.get("day_5_price"),
            "day_5_pct": ihsg_pred.get("day_5_pct"),
            "day_7_price": ihsg_pred.get("day_7_price"),
            "day_7_pct": ihsg_pred.get("day_7_pct"),
            "reasoning": ihsg_pred.get("reasoning"),
            "key_drivers": json.dumps(ihsg_pred.get("key_drivers", [])),
            "risks": json.dumps(ihsg_pred.get("risks", [])),
            "component_scores": json.dumps(ihsg_pred.get("component_scores", {})),
            "ihsg_trend": ihsg_pred.get("ihsg_trend"),
            "macro_signal": ihsg_pred.get("macro_signal"),
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
