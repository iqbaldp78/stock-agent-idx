"""
IHSG Data Fetcher
Mengambil IHSG OHLCV (8 tahun), market breadth (LQ45), sector rotation.
"""
import logging
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timedelta

from config import get_universe, to_yahoo_ticker

logger = logging.getLogger(__name__)

# === OHLCV ===

def get_ihsg_ohlcv(period: str = "8y") -> pd.DataFrame | None:
    """
    Fetch IHSG OHLCV untuk 8 tahun (default).
    Returns: DataFrame dengan Date index, OHLCV columns, atau None jika error.
    """
    try:
        ticker = yf.Ticker("^JKSE")
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning("[IHSG OHLCV] Empty history, return None")
            return None
        hist.index.name = "Date"
        return hist
    except Exception as e:
        logger.error(f"[IHSG OHLCV] Error: {e}")
        return None


# === MARKET BREADTH ===

def _get_lq45_ticker_data() -> dict[str, pd.DataFrame]:
    """
    Fetch semua LQ45 tickers OHLCV secara parallel.
    Returns: {ticker: DataFrame}
    """
    universe = get_universe()
    tickers = universe[:45]  # LQ45 saja

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_fetch_single_ohlcv, t): t
            for t in tickers
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    results[ticker] = df
            except Exception as e:
                logger.warning(f"[LQ45 fetch] {ticker}: {e}")

    return results


def _fetch_single_ohlcv(ticker: str, period: str = "3mo") -> pd.DataFrame | None:
    """Fetch single ticker OHLCV."""
    try:
        yahoo_ticker = to_yahoo_ticker(ticker)
        df = yf.download(yahoo_ticker, period=period, progress=False)
        return df
    except Exception as e:
        logger.warning(f"[fetch_single {ticker}] {e}")
        return None


def _calculate_ma(prices: pd.Series, window: int) -> pd.Series:
    """Calculate moving average."""
    return prices.rolling(window=window, min_periods=1).mean()


def get_market_breadth() -> dict:
    """
    Calculate market breadth: A/D ratio, participation, volume trend.

    Returns:
    {
        "advance_decline_ratio": float,
        "breadth_momentum": float,  # % change from 5d avg
        "volume_trend": float,      # % change from 20d avg
        "participation_above_ma20": float,  # % of LQ45 above MA20
        "timestamp": datetime,
    }
    """
    try:
        tickers_data = _get_lq45_ticker_data()

        if not tickers_data:
            logger.warning("[Market breadth] No ticker data, return neutral")
            return _neutral_breadth()

        # Count gainers/losers (today vs yesterday)
        gainers = 0
        losers = 0
        above_ma20 = 0
        total_volume = 0

        for ticker, df in tickers_data.items():
            if len(df) < 2:
                continue

            # Today vs yesterday
            today_close = df.iloc[-1]["Close"]
            yesterday_close = df.iloc[-2]["Close"]

            if today_close > yesterday_close:
                gainers += 1
            else:
                losers += 1

            # MA20 check
            if len(df) >= 20:
                ma20 = _calculate_ma(df["Close"], 20).iloc[-1]
                if today_close > ma20:
                    above_ma20 += 1

            # Volume
            total_volume += df.iloc[-1]["Volume"]

        total_tickers = gainers + losers
        if total_tickers == 0:
            return _neutral_breadth()

        # A/D ratio
        ad_ratio = gainers / max(losers, 1)

        # Participation above MA20
        participation = (above_ma20 / total_tickers * 100) if total_tickers > 0 else 50

        # Volume trend (simplified: compare recent avg vs 20d avg)
        recent_volumes = []
        for ticker, df in tickers_data.items():
            if len(df) >= 20:
                recent_avg = df["Volume"].tail(5).mean()
                vol_20d = df["Volume"].tail(20).mean()
                if vol_20d > 0:
                    recent_volumes.append((recent_avg - vol_20d) / vol_20d * 100)

        volume_trend = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0

        # Breadth momentum: compare today's A/D vs 5d avg
        adr_5d = ad_ratio  # Simplified (should track 5-day history ideally)
        breadth_momentum = 0  # Placeholder

        return {
            "advance_decline_ratio": round(ad_ratio, 2),
            "breadth_momentum": round(breadth_momentum, 2),
            "volume_trend": round(volume_trend, 2),
            "participation_above_ma20": round(participation, 1),
            "gainers": gainers,
            "losers": losers,
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"[Market breadth] Error: {e}")
        return _neutral_breadth()


def _neutral_breadth() -> dict:
    """Return neutral breadth values."""
    return {
        "advance_decline_ratio": 1.0,
        "breadth_momentum": 0.0,
        "volume_trend": 0.0,
        "participation_above_ma20": 50.0,
        "gainers": 0,
        "losers": 0,
        "timestamp": datetime.now(),
    }


# === SECTOR ROTATION ===

def get_sector_rotation() -> dict:
    """
    Fetch 5 sector performance (perbankan, mining, consumer, infrastructure, property).

    Returns:
    {
        "sectors": {
            "perbankan": {"price": float, "1d_return": float, "5d_return": float},
            ...
        },
        "divergence": float,  # max_return - min_return
        "leading_sector": str,
    }
    """
    try:
        # Indonesian sector tickers (approximation using main stocks)
        sector_map = {
            "perbankan": ["BBCA", "BBRI", "BMRI"],
            "mining": ["ANTM", "INCO"],
            "consumer": ["UNVR", "ICBP", "INDF"],
            "infrastructure": ["WIKA", "WSKT"],
            "property": ["PPRO", "SMDC"],
        }

        sector_returns = {}

        for sector_name, ticker_list in sector_map.items():
            prices_1d = []
            prices_5d = []

            for ticker in ticker_list:
                try:
                    df = _fetch_single_ohlcv(ticker, period="1mo")
                    if df is not None and len(df) >= 5:
                        today = df.iloc[-1]["Close"]
                        yesterday = df.iloc[-2]["Close"]
                        five_days_ago = df.iloc[-5]["Close"]

                        return_1d = (today - yesterday) / yesterday * 100 if yesterday != 0 else 0
                        return_5d = (today - five_days_ago) / five_days_ago * 100 if five_days_ago != 0 else 0

                        prices_1d.append(return_1d)
                        prices_5d.append(return_5d)
                except Exception as e:
                    logger.warning(f"[Sector {sector_name}/{ticker}] {e}")

            if prices_1d:
                avg_1d = sum(prices_1d) / len(prices_1d)
                avg_5d = sum(prices_5d) / len(prices_5d) if prices_5d else avg_1d
                sector_returns[sector_name] = {
                    "1d_return": round(avg_1d, 2),
                    "5d_return": round(avg_5d, 2),
                    "stocks_sampled": len(prices_1d),
                }

        if not sector_returns:
            return _neutral_sectors()

        returns_1d = [v["1d_return"] for v in sector_returns.values()]
        divergence = max(returns_1d) - min(returns_1d)
        leading = max(sector_returns.items(), key=lambda x: x[1]["1d_return"])[0]

        return {
            "sectors": sector_returns,
            "divergence": round(divergence, 2),
            "leading_sector": leading,
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"[Sector rotation] Error: {e}")
        return _neutral_sectors()


def _neutral_sectors() -> dict:
    """Return neutral sector values."""
    return {
        "sectors": {
            "perbankan": {"1d_return": 0.0, "5d_return": 0.0},
            "mining": {"1d_return": 0.0, "5d_return": 0.0},
            "consumer": {"1d_return": 0.0, "5d_return": 0.0},
            "infrastructure": {"1d_return": 0.0, "5d_return": 0.0},
            "property": {"1d_return": 0.0, "5d_return": 0.0},
        },
        "divergence": 0.0,
        "leading_sector": "neutral",
        "timestamp": datetime.now(),
    }
