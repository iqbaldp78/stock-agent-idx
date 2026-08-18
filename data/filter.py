"""
Data Filter — Rule-Based (No LLM)
Menyaring universe saham berdasarkan volume dan market cap minimum.
Phase 1: ~55 saham → ~30 saham.
"""
import logging
from data.fetcher_stockbit import get_stock_info, get_ohlcv
from config import MIN_VOLUME, MIN_MARKET_CAP

logger = logging.getLogger(__name__)


def apply_filter(universe: list[str]) -> list[str]:
    """
    Filter saham berdasarkan:
    - Average volume 20 hari >= MIN_VOLUME (300.000)
    - Market cap >= MIN_MARKET_CAP (1 Triliun IDR)
    - Bonus score dari Candlestick Pattern (Win-Rate BEI) untuk ranking kandidat utama
    """
    from agents.candlestick_patterns import detect_candlestick_patterns

    candidate_scores = []

    for ticker in universe:
        try:
            info = get_stock_info(ticker)
            ohlcv = get_ohlcv(ticker, period="3m")

            # Skip jika tidak ada data OHLCV
            if ohlcv is None or ohlcv.empty:
                logger.info(f"[SKIP] {ticker} — no OHLCV data")
                continue

            # Cek average volume 20 hari terakhir (log info tanpa skip agar ML dapat dievaluasi untuk semua ticker)
            avg_vol = ohlcv["Volume"].tail(20).mean() if "Volume" in ohlcv.columns else 0
            if avg_vol < MIN_VOLUME:
                logger.info(f"[FILTER INFO] {ticker} — low volume ({avg_vol:,.0f} < {MIN_VOLUME:,})")

            # Cek market cap (log info tanpa skip)
            market_cap = info.get("market_cap")
            if market_cap is not None and market_cap < MIN_MARKET_CAP:
                logger.info(
                    f"[FILTER INFO] {ticker} — low market cap "
                    f"({market_cap/1e12:.2f}T < {MIN_MARKET_CAP/1e12:.0f}T)"
                )

            # Calculate Candlestick Pattern Score
            filter_score = 5.0  # base liquidity pass score
            patterns = detect_candlestick_patterns(ohlcv)
            pat_names = []
            if patterns:
                for pat in patterns:
                    win_rate = pat.get("win_rate_bei", 0.60)
                    sig = pat.get("signal", "")
                    pat_names.append(f"{pat['name']} ({int(win_rate*100)}%)")
                    if sig in ["BULLISH", "STRONG BULLISH"]:
                        filter_score += win_rate * 5.0  # Boost +3.0 to +3.6
                    elif sig == "BEARISH":
                        filter_score -= win_rate * 5.0  # Penalty -3.0 to -3.5

            mcap_str = f"{market_cap/1e12:.2f}T" if market_cap else "N/A"
            pat_str = f" | Patterns: {', '.join(pat_names)}" if pat_names else ""
            logger.info(
                f"[PASS] {ticker} — score={filter_score:.1f}, vol={avg_vol:,.0f}, mcap={mcap_str}{pat_str}"
            )
            candidate_scores.append((ticker, filter_score))

        except Exception as e:
            logger.warning(f"[ERROR] {ticker} — {e}")
            continue

    # Sort candidates by filter_score descending so stocks with strong bullish candlestick patterns rank first
    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    candidates = [item[0] for item in candidate_scores]

    logger.info(f"Filter result: {len(candidates)}/{len(universe)} passed (sorted by Candlestick & Liquidity score)")
    return candidates
