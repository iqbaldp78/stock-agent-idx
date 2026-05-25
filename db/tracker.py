"""
DB — Tracker
Menyimpan hasil analisis ke PostgreSQL.
"""
import json
from datetime import date
from sqlalchemy.orm import Session
from db import SessionLocal
from db.models import AgentScore, DebateLog, Signal


def save_scores(run_date: date, scores: dict, composites: dict,
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
                run_date=run_date,
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


def save_debate_log(run_date: date, debate_log: list) -> None:
    """Simpan log debat ke tabel debate_logs."""
    db: Session = SessionLocal()
    try:
        for entry in debate_log:
            record = DebateLog(
                run_date=run_date,
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


def save_signals(run_date: date, top_picks: list, scores: dict) -> None:
    """Simpan final signals ke tabel signals."""
    db: Session = SessionLocal()
    try:
        for pick in top_picks:
            ticker = pick["ticker"]
            ticker_scores = scores.get(ticker, {})
            bandarm = ticker_scores.get("bandarm", {})
            price_analysis = bandarm.get("price_analysis", {})

            # Parse entry zone
            entry_zone = pick.get("entry_zone", "")
            entry_low = None
            entry_high = None
            if "–" in str(entry_zone):
                parts = str(entry_zone).split("–")
                try:
                    entry_low = float(parts[0].replace(",", "").replace(".", ""))
                    entry_high = float(parts[1].replace(",", "").replace(".", ""))
                except (ValueError, IndexError):
                    pass

            record = Signal(
                run_date=run_date,
                ticker=ticker,
                rank=pick.get("rank"),
                signal="BUY",
                entry_low=entry_low,
                entry_high=entry_high,
                max_entry=_parse_number(pick.get("max_entry")),
                target_1=_parse_number(pick.get("target_1")),
                stop_loss=_parse_number(pick.get("stop_loss")),
                conviction=pick.get("conviction"),
                thesis=f"{pick.get('bandarm_signal', '')} — composite {pick.get('composite_score', '')}",
                entry_reasoning=f"Entry berdasarkan avg cost bandar",
                bandar_avg_7d=price_analysis.get("bandar_avg_7d"),
                bandar_avg_1m=price_analysis.get("bandar_avg_1m"),
                broker_utama=", ".join(pick.get("broker_to_watch", [])),
                time_horizon="Positional (4-6 minggu)",
                weight_mode=pick.get("weight_mode"),
                composite_score=pick.get("composite_score"),
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def save_full_result(result: dict) -> None:
    """Simpan semua hasil analisis sekaligus."""
    today = date.today()

    if result.get("composites"):
        save_scores(today, result["scores"], result["composites"], result["macro_data"])

    if result.get("debate_log"):
        save_debate_log(today, result["debate_log"])

    if result.get("top_picks"):
        save_signals(today, result["top_picks"], result["scores"])


def _parse_number(value) -> float | None:
    """Parse string number ke float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace(".", "").strip())
    except (ValueError, TypeError):
        return None
