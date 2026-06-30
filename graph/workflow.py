"""
Graph — LangGraph Workflow
Orchestrasi full pipeline: Filter → Scoring → Debate → Decision
"""
from __future__ import annotations

from typing import TypedDict
from langgraph.graph import StateGraph, END

from data.filter import apply_filter
from data.fetcher_stockbit import get_stock_info
from agents.fundamental import analyze as fund_analyze
from agents.technical import analyze as tech_analyze
from agents.bandarmologi import analyze as bandarm_analyze
from agents.macro import analyze as macro_analyze
from agents.news import analyze as news_analyze
from agents.investment_manager import synthesize as im_synthesize
from agents.ihsg_predictor import predict_ihsg
from models.multiday_predictor import MultiDayPredictor
from data.ml_features import extract_features
from data.fetcher_stockbit import get_ohlcv
from agents.debate import run_llm_debate
from agents.debate.logging_utils import log_debate_turn, log_debate_section, log_finalists
from agents.llm_client import health_check
from graph.scoring import calculate_composite
from config import LLM_ENABLED, get_universe
from agents.commodity_integration import (
    add_commodity_context_to_macro,
    enrich_ticker_with_commodities,
)
from agents.commodity_price_discovery import (
    analyze_with_price_discovery,
    calculate_adjusted_commodity_bonus,
)

import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    universe: list
    candidates: list
    macro_data: dict
    scores: dict          # {ticker: {agent: result}}
    composites: dict      # {ticker: composite_result}
    ml_predictions: dict  # {ticker: ml_result}
    ihsg_prediction: dict # IHSG predictor output
    debate_log: list
    finalists: list
    top_picks: list
    final_report: dict


# === Node Functions ===

def run_filter(state: AgentState) -> dict:
    """Phase 1: Rule-based filter ~55 → ~30 saham."""
    universe = state.get("universe") or get_universe()
    logger.info(f"[FILTER] Input: {len(universe)} tickers")

    candidates = apply_filter(universe)
    logger.info(f"[FILTER] Output: {len(candidates)} candidates")

    return {"candidates": candidates, "universe": universe}


def run_parallel_scoring(state: AgentState) -> dict:
    """Phase 2: Score semua candidates dengan 4 agent + composite."""
    candidates = state["candidates"]
    logger.info(f"[SCORING] Scoring {len(candidates)} candidates")

    # Macro data (shared for all tickers)
    macro_data = macro_analyze()

    # Add commodity market context
    try:
        macro_data = add_commodity_context_to_macro(macro_data)
        logger.info("[SCORING] Commodity context added to macro_data")
    except Exception as e:
        logger.warning(f"[SCORING] Failed to add commodity context: {e}")

    is_volatile = macro_data["is_volatile"]

    scores = {}
    composites = {}

    for ticker in candidates:
        try:
            # Run all agents
            bandarm = bandarm_analyze(ticker)
            tech = tech_analyze(ticker)
            fund = fund_analyze(ticker)
            news = news_analyze(ticker)

            # Get market cap for weight selection
            info = get_stock_info(ticker)
            market_cap = info.get("market_cap") or 0

            # Store individual scores
            scores[ticker] = {
                "bandarm": bandarm,
                "technical": tech,
                "fundamental": fund,
                "news": news,
            }

            # Check for missing scores due to agent errors
            if "score" not in bandarm or "score" not in tech or "score" not in fund:
                logger.warning(f"  [{ticker}] ERROR: Missing score from one of the agents (Bandarm: {'score' in bandarm}, Tech: {'score' in tech}, Fund: {'score' in fund})")
                continue

            # Calculate composite
            agent_scores = {
                "bandarm": bandarm["score"],
                "technical": tech["score"],
                "fundamental": fund["score"],
                "macro": macro_data.get("score", 5.0),
                "news": news.get("score", 5.0),
            }
            composite = calculate_composite(agent_scores, ticker, market_cap, is_volatile, macro_data)

            # === COMMODITY ANALYSIS WITH PRICE DISCOVERY ===
            try:
                commodity_analysis = analyze_with_price_discovery(ticker)

                if commodity_analysis.get("commodities") and not commodity_analysis.get("error"):
                    # Calculate adjusted bonus based on price discovery
                    commodity_bonus, commodity_narrative = calculate_adjusted_commodity_bonus(commodity_analysis)

                    # Apply bonus to composite score
                    if commodity_bonus != 0:
                        old_composite = composite["composite_score"]
                        new_composite = max(1.0, min(10.0, old_composite + commodity_bonus))
                        composite["composite_score"] = new_composite
                        composite["commodity_bonus"] = commodity_bonus
                        composite["commodity_narrative"] = commodity_narrative
                        composite["composite_before_commodity"] = old_composite

                        logger.info(
                            f"  [{ticker}] Commodity adjustment: {old_composite} → {new_composite} "
                            f"({commodity_bonus:+.2f}) | {commodity_narrative}"
                        )

                    # Store commodity analysis for debate phase
                    composite["commodity_analysis"] = commodity_analysis
            except Exception as e:
                logger.warning(f"  [{ticker}] Commodity analysis failed: {e}")

            composites[ticker] = composite

            logger.info(f"  [{ticker}] composite={composite['composite_score']} mode={composite['weight_mode']}")

        except Exception as e:
            logger.warning(f"  [{ticker}] ERROR: {e}")
            continue

    return {
        "scores": scores,
        "composites": composites,
        "macro_data": macro_data,
    }


def run_ml_prediction(state: AgentState) -> dict:
    """Phase 2.7: Machine Learning Day-1 Forecast."""
    composites = state.get("composites", {})
    scores = state.get("scores", {})
    macro_data = state.get("macro_data", {})

    if not composites:
        return {"ml_predictions": {}}

    logger.info(f"[ML] Running Multi-Day forecast for {len(composites)} tickers")

    predictor = MultiDayPredictor()
    ml_results = {}

    # Sort by composite score to only run ML on top candidates (performance optimization)
    sorted_tickers = sorted(composites.keys(), key=lambda t: composites[t]["composite_score"], reverse=True)
    top_candidates = sorted_tickers[:12] # Limit to top 12

    for ticker in top_candidates:
        try:
            # 1. Fetch recent OHLCV for features
            ohlcv = get_ohlcv(ticker, period="3mo")

            # 2. Extract feature vector
            feature_row = extract_features(ticker, scores, macro_data, ohlcv)

            # 3. Predict Multi-Day
            preds = predictor.predict(feature_row)

            # Format predictions to percentages
            pred_pcts = {h: round(val * 100, 2) for h, val in preds.items()}

            # Use 1d prediction for the main signal/direction
            signal = predictor.get_signal(preds.get('1d', 0.0))

            ml_results[ticker] = {
                "pred_return": pred_pcts.get('1d', 0.0), # Main 1d return
                "predictions_multiday": pred_pcts,       # 1d, 3d, 5d, 7d
                "signal": signal,
                "confidence": "MEDIUM" # Default for now
            }

            # Inject to composites so downstream agents (like Price Predictor) can access it easily
            if ticker in composites:
                composites[ticker]["ml_prediction"] = ml_results[ticker]

            logger.info(f"  [{ticker}] ML Pred (1d/3d/5d/7d): {pred_pcts.get('1d',0):+.2f}% / {pred_pcts.get('3d',0):+.2f}% / {pred_pcts.get('5d',0):+.2f}% / {pred_pcts.get('7d',0):+.2f}% -> {signal}")
        except Exception as e:
            logger.warning(f"  [{ticker}] ML Error: {e}")

    return {"ml_predictions": ml_results}


def run_ihsg_prediction(state: AgentState) -> dict:
    """Phase 2.5: IHSG direction forecast (before debate)."""
    try:
        ihsg_pred = predict_ihsg()
        logger.info(f"[IHSG] {ihsg_pred.get('direction')} ({ihsg_pred.get('confidence')})")
        return {"ihsg_prediction": ihsg_pred}
    except Exception as e:
        logger.warning(f"[IHSG Prediction] Error: {e}")
        return {"ihsg_prediction": {}}


def run_debate_rule_based(state: AgentState) -> dict:
    """
    Phase 3 fallback: Rule-based debate — 2 rounds.
    """
    scores = state["scores"]
    composites = state["composites"]
    macro_data = state["macro_data"]
    ml_predictions = state.get("ml_predictions", {})

    if not composites:
        return {"debate_log": [], "finalists": []}

    sorted_tickers = sorted(
        composites.items(),
        key=lambda x: x[1]["composite_score"],
        reverse=True,
    )

    debate_candidates = sorted_tickers[:min(15, len(sorted_tickers))]
    debate_log = []

    log_debate_section(f"DEBAT MULTI-AGENT (rule-based) — {len(debate_candidates)} ticker")
    logger.info("[DEBATE] Round 1 — Initial Arguments (rule-based)")
    round1_votes = {}

    def _log(entry: dict) -> None:
        debate_log.append(entry)
        log_debate_turn(entry, source="rule")

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})
        fund = ticker_scores.get("fundamental", {})

        votes_for = 0
        votes_against = 0

        bandarm_score = bandarm.get("score", 5)
        if bandarm_score >= 7:
            argument = f"{ticker}: {bandarm.get('signal', 'N/A')} — bandar aktif akumulasi"
            vote = "BUY"
            votes_for += 0.40
        elif bandarm_score <= 4:
            argument = f"{ticker}: distribusi terdeteksi — hindari"
            vote = "SELL"
            votes_against += 0.40
        else:
            argument = f"{ticker}: netral — tidak ada sinyal kuat dari bandar"
            vote = "HOLD"

        _log({
            "round": 1, "ticker": ticker, "agent": "bandarmologi",
            "argument": argument, "vote": vote,
        })

        tech_score = tech.get("score", 5)
        if tech_score >= 7:
            argument = f"{ticker}: {tech.get('setup', 'setup bullish')}"
            vote = "BUY"
            votes_for += 0.25
        elif tech_score <= 4:
            argument = f"{ticker}: chart bearish, hindari"
            vote = "SELL"
            votes_against += 0.25
        else:
            argument = f"{ticker}: chart netral, belum ada trigger"
            vote = "HOLD"

        _log({
            "round": 1, "ticker": ticker, "agent": "technical",
            "argument": argument, "vote": vote,
        })

        fund_score = fund.get("score", 5)
        if fund_score >= 7:
            key_pts = "; ".join(fund.get("key_points", [])[:2])
            argument = f"{ticker}: fundamental solid — {key_pts}"
            vote = "BUY"
            votes_for += 0.20
        elif fund_score <= 4:
            risks = "; ".join(fund.get("risks", [])[:2])
            argument = f"{ticker}: fundamental lemah — {risks}"
            vote = "SELL"
            votes_against += 0.20
        else:
            argument = f"{ticker}: fundamental cukup, tidak outstanding"
            vote = "HOLD"

        _log({
            "round": 1, "ticker": ticker, "agent": "fundamental",
            "argument": argument, "vote": vote,
        })

        macro_score = macro_data.get("score", 5)
        if macro_score >= 7:
            argument = f"Pasar bullish, mendukung {ticker}"
            vote = "BUY"
            votes_for += 0.15
        elif macro_score <= 4:
            argument = f"Pasar bearish, risk tinggi untuk {ticker}"
            vote = "SELL"
            votes_against += 0.15
        else:
            argument = f"Pasar netral, {ticker} tergantung micro"
            vote = "HOLD"

        _log({
            "round": 1, "ticker": ticker, "agent": "macro",
            "argument": argument, "vote": vote,
        })

        # News agent contribution
        news = ticker_scores.get("news", {})
        news_score = news.get("score", 5)
        if news_score >= 7:
            argument = f"{ticker}: {news.get('summary', 'sentimen berita positif')}"
            vote = "BUY"
            votes_for += 0.12
        elif news_score <= 4:
            argument = f"{ticker}: berita negatif, hindari untuk sementara"
            vote = "SELL"
            votes_against += 0.12
        else:
            argument = f"{ticker}: berita netral, tidak ada sentimen kuat"
            vote = "HOLD"

        _log({
            "round": 1, "ticker": ticker, "agent": "news",
            "argument": argument, "vote": vote,
        })

        round1_votes[ticker] = {
            "votes_for": votes_for,
            "votes_against": votes_against,
            "net_vote": votes_for - votes_against,
        }

    logger.info("[DEBATE] Round 2 — Cross-Examination (rule-based)")

    for ticker, composite in debate_candidates:
        ticker_scores = scores.get(ticker, {})
        bandarm = ticker_scores.get("bandarm", {})
        tech = ticker_scores.get("technical", {})

        bandarm_score = bandarm.get("score", 5)
        tech_score = tech.get("score", 5)

        if bandarm_score >= 7 and tech_score <= 5:
            argument = (
                f"Bandarm override: {ticker} bandar akumulasi kuat meski chart belum confirm"
            )
            round1_votes[ticker]["net_vote"] += 0.10
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "BUY",
            })

        elif bandarm_score <= 4 and tech_score >= 7:
            argument = f"Bandarm warning: {ticker} chart oke tapi bandar distribusi — trap potential"
            round1_votes[ticker]["net_vote"] -= 0.15
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "SELL",
            })

        bd_7 = bandarm.get("window_7d", {}).get("net_value", 0)
        if isinstance(bd_7, (int, float)) and bd_7 > 0 and bandarm_score >= 6:
            argument = f"{ticker}: net value positif konfirmasi akumulasi bandar"
            round1_votes[ticker]["net_vote"] += 0.05
            _log({
                "round": 2, "ticker": ticker, "agent": "bandarmologi",
                "argument": argument, "vote": "BUY",
            })

    logger.info("[DEBATE] Synthesis — selecting finalists")

    def _ml_bonus(ml_pred: dict | None) -> float:
        if not ml_pred:
            return 0.0
        pred_return = float(ml_pred.get("pred_return", 0.0))
        signal = str(ml_pred.get("signal", "")).upper()
        base = max(-0.8, min(0.8, pred_return * 0.30))
        signal_boost = 0.0
        if signal == "STRONG BUY":
            signal_boost = 0.20
        elif signal == "BUY":
            signal_boost = 0.10
        elif signal == "AVOID":
            signal_boost = -0.20
        return round(base + signal_boost, 3)

    final_ranking = []
    for ticker, composite in debate_candidates:
        debate_bonus = round1_votes.get(ticker, {}).get("net_vote", 0)
        ml_bonus = _ml_bonus(ml_predictions.get(ticker))
        final_score = composite["composite_score"] + debate_bonus + ml_bonus
        final_ranking.append((ticker, final_score, composite, ml_bonus))

    final_ranking.sort(key=lambda x: x[1], reverse=True)

    finalists = [
        {
            "ticker": ticker,
            "final_score": round(score, 2),
            "composite_score": comp["composite_score"],
            "weight_mode": comp["weight_mode"],
            "debate_bonus": round(score - comp["composite_score"] - ml_bonus, 2),
            "ml_bonus": round(ml_bonus, 2),
        }
        for ticker, score, comp, ml_bonus in final_ranking[:7]
    ]

    log_finalists(finalists)

    return {
        "debate_log": debate_log,
        "finalists": finalists,
    }


def run_debate(state: AgentState) -> dict:
    """
    Phase 3: LLM multi-agent debate via 9Router, with rule-based fallback.
    """
    if LLM_ENABLED and health_check():
        try:
            return run_llm_debate(state)
        except Exception as e:
            logger.warning("LLM debate failed, fallback rule-based: %s", e)
    elif LLM_ENABLED:
        logger.warning("9Router health_check failed, using rule-based debate")
    return run_debate_rule_based(state)


def run_investment_manager(state: AgentState) -> dict:
    """
    Phase 4: Investment Manager — select TOP 3 picks.
    """
    return im_synthesize(state)


# === Build Workflow ===

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("filter", run_filter)
    workflow.add_node("scoring", run_parallel_scoring)
    workflow.add_node("ihsg", run_ihsg_prediction)
    workflow.add_node("ml", run_ml_prediction)
    workflow.add_node("debate", run_debate)
    workflow.add_node("decision", run_investment_manager)

    workflow.set_entry_point("filter")
    workflow.add_edge("filter", "scoring")
    workflow.add_edge("scoring", "ihsg")
    workflow.add_edge("ihsg", "ml")
    workflow.add_edge("ml", "debate")
    workflow.add_edge("debate", "decision")
    workflow.add_edge("decision", END)

    return workflow.compile()


def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "y", "on")


def _already_trained_today(meta_path: Path) -> bool:
    if not meta_path.exists():
        return False
    try:
        with meta_path.open("r") as f:
            meta = json.load(f)
        run_date = meta.get("run_date")
        if not run_date:
            return False
        return datetime.fromisoformat(run_date).date() == date.today()
    except Exception:
        return False


def maybe_train_ml_before_analysis(universe: list[str] | None = None) -> None:
    """Train ML model once per day before full analysis, guarded by quality gate."""
    if not _bool_env("ML_AUTO_TRAIN", True):
        logger.info("[ML TRAIN] Auto training disabled via ML_AUTO_TRAIN")
        return

    meta_path = Path(os.getenv("ML_MODEL_META_PATH", "models/checkpoints/lgbm_multiday_meta.json"))
    if _already_trained_today(meta_path):
        logger.info("[ML TRAIN] Skip: training already attempted today")
        return

    period = os.getenv("ML_AUTO_TRAIN_PERIOD", "1y")
    min_rows = os.getenv("ML_AUTO_TRAIN_MIN_ROWS", "120")

    cmd = [
        sys.executable,
        "scripts/train_multiday_model.py",
        "--period",
        period,
        "--min-rows",
        min_rows,
    ]
    if _bool_env("ML_AUTO_TRAIN_FORCE_SAVE", False):
        cmd.append("--force-save")
    if universe:
        cmd.append("--tickers")
        cmd.extend([str(t).upper() for t in universe])
    else:
        cmd.append("--all")

    logger.info("[ML TRAIN] Running before full analysis: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=False, text=True, capture_output=True)
        if result.stdout:
            logger.info("[ML TRAIN]\n%s", result.stdout.strip())
        if result.stderr:
            logger.warning("[ML TRAIN STDERR]\n%s", result.stderr.strip())
        if result.returncode != 0:
            logger.warning("[ML TRAIN] Training command exited with code %s", result.returncode)
    except Exception as e:
        logger.warning("[ML TRAIN] Auto training failed: %s", e)


def run_full_analysis(universe: list[str] | None = None, auto_train_ml: bool = True) -> dict:
    """Run the complete analysis pipeline."""
    if auto_train_ml:
        maybe_train_ml_before_analysis(universe=universe)

    from portfolio.manager import get_all_holdings
    try:
        holdings = get_all_holdings()
        portfolio_tickers = [h["ticker"] for h in holdings]
    except Exception as e:
        logger.warning(f"Failed to fetch portfolio holdings: {e}")
        portfolio_tickers = []

    final_universe = universe or get_universe()
    final_universe = list(set(final_universe + portfolio_tickers))

    app = build_workflow()
    initial_state = {
        "universe": final_universe,
        "candidates": [],
        "macro_data": {},
        "scores": {},
        "composites": {},
        "ml_predictions": {},
        "debate_log": [],
        "finalists": [],
        "top_picks": [],
        "final_report": {},
    }
    result = app.invoke(initial_state)
    return result
