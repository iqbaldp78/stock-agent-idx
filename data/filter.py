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
    - Average volume 20 hari >= MIN_VOLUME (1 juta)
    - Market cap >= MIN_MARKET_CAP (1 Triliun IDR)
    """
    candidates = []

    for ticker in universe:
        try:
            info = get_stock_info(ticker)
            ohlcv = get_ohlcv(ticker, period="1mo")

            # Skip jika tidak ada data OHLCV
            if ohlcv.empty:
                logger.info(f"[SKIP] {ticker} — no OHLCV data")
                continue

            # Cek average volume 20 hari terakhir
            avg_vol = ohlcv["Volume"].tail(20).mean()
            if avg_vol < MIN_VOLUME:
                logger.info(f"[SKIP] {ticker} — low volume ({avg_vol:,.0f} < {MIN_VOLUME:,})")
                continue

            # Cek market cap (skip jika data tidak tersedia — LQ45 sudah big cap)
            market_cap = info.get("market_cap")
            if market_cap is not None and market_cap < MIN_MARKET_CAP:
                logger.info(
                    f"[SKIP] {ticker} — low market cap "
                    f"({market_cap/1e12:.2f}T < {MIN_MARKET_CAP/1e12:.0f}T)"
                )
                continue

            candidates.append(ticker)
            mcap_str = f"{market_cap/1e12:.2f}T" if market_cap else "N/A"
            logger.info(
                f"[PASS] {ticker} — vol={avg_vol:,.0f}, mcap={mcap_str}"
            )

        except Exception as e:
            logger.warning(f"[ERROR] {ticker} — {e}")
            continue

    logger.info(f"Filter result: {len(candidates)}/{len(universe)} passed")
    return candidates
