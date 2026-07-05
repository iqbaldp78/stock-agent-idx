"""
Feature Engineering for ML Prediction
Mengonversi output agent (JSON) dan data raw (OHLCV) menjadi fitur numerik.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "ticker_id",
    "bandarm_score",
    "dist_avg_7d",
    "dist_avg_1m",
    "foreign_net_7d",
    "foreign_net_1m",
    "top3_buy_ratio_7d",
    "top3_sell_ratio_7d",
    "retail_buy_ratio_7d",
    "retail_sell_ratio_7d",
    "top3_buy_ratio_1m",
    "top3_sell_ratio_1m",
    "is_retail_accum",
    "technical_score",
    "rsi",
    "is_bullish_trend",
    "is_rsi_divergence",
    "is_macd_divergence",
    "vol_ratio",
    "macro_score",
    "ihsg_vs_ma20",
    "usdidr_val",
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "volatility_20d",
    "gap_open",
    "ma_dist_20",
    "ma_dist_50",
    "volume_spike",
    "support_proximity",
    "resistance_proximity",
    "range_pct",
    "macd",
    "macd_hist",
    "bb_upper_dist",
    "bb_lower_dist",
    "stoch_k",
    "stoch_d",
    "atr",
    # Volume profile / orderbook proxy
    "vol_profile_20d_upper",
    "vol_profile_20d_mid",
    "vol_profile_20d_lower",
    "vwap_deviation_20d",
    "signed_volume_20d",
    "ob_imbalance_proxy_20d",
    "range_concentration_20d",
    # Day-1 specific features
    "close_to_high",
    "close_to_low",
    "body_ratio",
    "ret_1d_zscore",
    "vol_trend_5d",
    "day_of_week",
    "gap_continuation",
    "ret_2d",
    "ret_10d",
    "rsi_14_prev",
    "volume_spike_prev",
    # Market context features (IHSG)
    "ihsg_ret_1d",
    "ihsg_ret_5d",
    "ihsg_rsi",
    "ihsg_ma_dist_20",
    "ihsg_volatility",
    "ihsg_trend",
    "stock_vs_ihsg_1d",
    # Foreign flow features
    "foreign_flow_zscore",
]

# Kolom yang benar-benar digunakan untuk melatih ML (hanya yang bisa dihitung secara historis)
ML_TRAIN_FEATURES = [
    # ── Proven useful (importance > 0) ──────────────────────────────────
    "dist_avg_7d",
    "foreign_net_7d",
    "rsi",
    "is_bullish_trend",
    "vol_ratio",
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "volatility_20d",
    "gap_open",
    "ma_dist_20",
    "ma_dist_50",
    "volume_spike",
    "range_pct",
    "macd",
    "macd_hist",
    "bb_upper_dist",
    "bb_lower_dist",
    "stoch_k",
    "stoch_d",
    "atr",
    # Volume profile (only useful ones)
    "vwap_deviation_20d",
    "ob_imbalance_proxy_20d",
    "range_concentration_20d",
    # Day-1 specific features
    "close_to_high",
    "close_to_low",
    "body_ratio",
    "ret_1d_zscore",
    "vol_trend_5d",
    "day_of_week",
    "gap_continuation",
    "ret_2d",
    "ret_10d",
    "rsi_14_prev",
    "volume_spike_prev",
    # Market context features (IHSG)
    "ihsg_ret_1d",
    "ihsg_ret_5d",
    "ihsg_rsi",
    "ihsg_ma_dist_20",
    "ihsg_volatility",
    "ihsg_trend",
    "stock_vs_ihsg_1d",
    # Foreign flow features
    "foreign_flow_zscore",
]

# ─── IHSG History Cache ──────────────────────────────────────────────────────
_ihsg_cache = None

def _fetch_ihsg_history() -> pd.DataFrame | None:
    """Fetch IHSG OHLCV from DB for market context features. Cached in memory."""
    global _ihsg_cache
    if _ihsg_cache is not None:
        return _ihsg_cache
    try:
        from db import SessionLocal
        from db.models import IhsgOhlcv
        db = SessionLocal()
        try:
            rows = db.query(IhsgOhlcv).order_by(IhsgOhlcv.trade_date).all()
            if not rows:
                return None
            _ihsg_cache = pd.DataFrame([{
                'open': float(r.open or 0),
                'high': float(r.high or 0),
                'low': float(r.low or 0),
                'close': float(r.close or 0),
                'volume': int(r.volume or 0),
            } for r in rows], index=pd.to_datetime([r.trade_date for r in rows]))
            logger.info(f"Loaded IHSG history: {len(_ihsg_cache)} rows ({_ihsg_cache.index.min().date()} to {_ihsg_cache.index.max().date()})")
            return _ihsg_cache
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to fetch IHSG history: {e}")
        return None

def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def _compute_macd(series: pd.Series, fast=12, slow=26, signal=9) -> tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_hist

def _compute_bb(series: pd.Series, window=20, num_std=2) -> tuple[pd.Series, pd.Series]:
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    upper = rolling_mean + (rolling_std * num_std)
    lower = rolling_mean - (rolling_std * num_std)
    return upper, lower

def _compute_stoch(high: pd.Series, low: pd.Series, close: pd.Series, k_window=14, d_window=3) -> tuple[pd.Series, pd.Series]:
    min_low = low.rolling(window=k_window).min()
    max_high = high.rolling(window=k_window).max()
    k = 100 * (close - min_low) / (max_high - min_low)
    d = k.rolling(window=d_window).mean()
    return k, d

def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, window=14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr


def _parse_number(val: object, default: float = 0.0) -> float:
    if isinstance(val, (int, float, np.number)):
        return float(val)
    if val is None:
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return default


def _parse_pct(val: object, default: float = 0.0) -> float:
    if isinstance(val, (int, float, np.number)):
        return float(val)
    if val is None:
        return default
    try:
        return float(str(val).replace("%", "").replace("+", "").replace(",", "").strip())
    except Exception:
        return default


def _extract_first_numeric(data_used: list, key: str, default: float) -> float:
    if not isinstance(data_used, list):
        return default
    for item in data_used:
        if not isinstance(item, str) or key not in item:
            continue
        try:
            return float(item.split(":")[-1].strip())
        except Exception:
            continue
    return default


def _ticker_id(ticker: str) -> int:
    try:
        return abs(hash(str(ticker).upper())) % 10000
    except Exception:
        return 0


# Fallback manual sector mapping until DB has sector column.
# Lowered ticker -> sector. Add as needed.
SECTOR_MAP: dict[str, str] = {
    "bbca": "banking",
    "bbri": "banking",
    "bbni": "banking",
    "bmri": "banking",
    "bjin": "banking",
    "bpan": "banking",
    "bsin": "banking",
    "btpn": "banking",
    "byna": "banking",
    "bbtb": "banking",
    "nisp": "banking",
    "maya": "banking",
    "arwa": "banking",
    "bbkp": "banking",
    "bbhg": "banking",
    "bbmd": "banking",
    "bbhi": "banking",
    "bbmg": "banking",
    "bhar": "banking",
    "bnba": "banking",
    "bsmi": "banking",
    "ibfc": "banking",
    "kbri": "banking",
    "mega": "banking",
    "niny": "banking",
    "bksw": "banking",
    "bles": "banking",
    "masb": "banking",
    "bvic": "banking",
    "bksi": "banking",
    "bbtb": "banking",
    "bbsw": "banking",
    "bbbm": "banking",
    "bbdn": "banking",
    "bbf1": "banking",
    "bbgp": "banking",
    "bbyd": "banking",
    "bbcu": "banking",
    "bbwt": "banking",
    "bbtp": "banking",
    "bbkp": "banking",
    "bbst": "banking",
    "bbhi": "banking",
    "bbss": "banking",
    "bbmg": "banking",
    "bbbv": "banking",
    "bbni": "banking",
    "bbca": "banking",
    "bbri": "banking",
    "bbtb": "banking",
    "bbtb": "banking",
    "bbtb": "banking",
    "bbca": "banking",
    "bbri": "banking",
    "bbni": "banking",
    "bmri": "banking",
    "btpn": "banking",
    "byna": "banking",
    "bsin": "banking",
    "bpan": "banking",
    "bjin": "banking",
    "masb": "banking",
    "bksw": "banking",
    "bles": "banking",
    "bbkp": "banking",
    "bbmd": "banking",
    "bbhg": "banking",
    "bbhi": "banking",
    "bbss": "banking",
    "bbmg": "banking",
    "bhar": "banking",
    "bnba": "banking",
    "bsmi": "banking",
    "ibfc": "banking",
    "kbri": "banking",
    "mega": "banking",
    "niny": "banking",
    "bbtb": "banking",
    "bbsw": "banking",
    "bbbm": "banking",
    "bbdn": "banking",
    "bbf1": "banking",
    "bbgp": "banking",
    "bbyd": "banking",
    "bbcu": "banking",
    "bbwt": "banking",
    "bbtp": "banking",
    "bbst": "banking",
    "bbbm": "banking",
    "asii": "automotive",
    "imba": "automotive",
    "simo": "automotive",
    "ptba": "mining",
    "inka": "mining",
    "hrta": "mining",
    "adro": "mining",
    "antm": "mining",
    "inco": "mining",
    "mdka": "mining",
    "byan": "mining",
    "dkft": "mining",
    "medc": "mining",
    "bssr": "mining",
    "itmg": "mining",
    "pgio": "mining",
    "ggzj": "mining",
    "indf": "consumer",
    "icbp": "consumer",
    "unvr": "consumer",
    "sido": "consumer",
    "ckra": "consumer",
    "myor": "consumer",
    "ultra": "infrastructure",
    "towr": "infrastructure",
    "tbig": "infrastructure",
    "wsbp": "infrastructure",
    "adhi": "infrastructure",
    "pada": "infrastructure",
    "wskt": "infrastructure",
    "pgas": "oil_gas",
    "cste": "oil_gas",
    "enrg": "oil_gas",
    "excl": "telecom",
    "tlkm": "telecom",
    "isat": "telecom",
    "fren": "telecom",
    "gtsi": "telecom",
    "inkl": "telecom",
    "amrt": "retail",
    "rasi": "retail",
    "mpmx": "retail",
    "mapi": "retail",
    "buka": "digital",
    "goto": "digital",
    "klbf": "pharma",
    "kaef": "pharma",
    "srae": "pharma",
    "ipca": "pharma",
    "pyfa": "pharma",
    "mnbm": "property",
    "bsde": "property",
    "lpdk": "property",
    "mgro": "property",
    "brpt": "chemical",
    "tins": "metal",
    "essa": "multifinance",
    "bris": "insurance",
    "bbtn": "banking",
    "bbmg": "multifinance",
    "smma": "multifinance",
    "tasa": "insurance",
    "afpn": "insurance",
    "inan": "insurance",
    "bima": "insurance",
    "jiwa": "insurance",
    "wncn": "insurance",
    "bsml": "insurance",
    "bsat": "insurance",
    "pins": "insurance",
    "asli": "insurance",
    "iclp": "insurance",
    "lifr": "insurance",
    "mlbi": "insurance",
    "pmfn": "multifinance",
    "mfmi": "multifinance",
    "apdn": "healthcare",
    "sraa": "healthcare",
    "srui": "healthcare",
    "srim": "healthcare",
    "srsx": "healthcare",
    "srti": "healthcare",
    "irdm": "healthcare",
    "rsia": "healthcare",
    "mens": "healthcare",
    "care": "healthcare",
    "vins": "healthcare",
    "mkfi": "healthcare",
    "avia": "healthcare",
    "rmai": "healthcare",
    "silo": "healthcare",
    "dvok": "healthcare",
    "saka": "healthcare",
    "mela": "healthcare",
    "psei": "healthcare",
    "heal": "healthcare",
    "psgj": "healthcare",
    "spma": "healthcare",
    "kios": "health_retail",
    "arco": "health_retail",
    "mari": "health_retail",
    "blbd": "health_retail",
    "pras": "education",
    "educ": "education",
    "scco": "education",
    "abda": "education",
    "hrme": "education",
    "tiga": "education",
    "mill": "retail",
    "cipc": "retail",
    "cccm": "retail",
    "bpii": "retail",
    "amad": "retail",
    "mofa": "retail",
    "bber": "retail",
    "casa": "retail",
    "srmr": "retail",
    "imjs": "retail",
    "prda": "retail",
    "roda": "retail",
    "gema": "retail",
    "ipla": "retail",
    "mktr": "retail",
    "viva": "media",
    "mncn": "media",
    "abmm": "media",
    "dmmx": "media",
    "mtra": "media",
    "sgem": "media",
    "edit": "media",
    "skrn": "media",
    "bdxs": "media",
    "ptai": "tech",
}
# Missing tickers -> 'unknown'
SECTOR_CATEGORIES = [
    "banking",
    "mining",
    "consumer",
    "infrastructure",
    "oil_gas",
    "telecom",
    "retail",
    "digital",
    "automotive",
    "pharma",
    "property",
    "construction",
    "metal",
    "chemical",
    "trading",
    "multifinance",
    "insurance",
    "healthcare",
    "education",
    "media",
    "tech",
    "health_retail",
    "unknown",
]


def _get_sector_id(sector_name: str) -> int:
    try:
        return SECTOR_CATEGORIES.index(sector_name.lower())
    except ValueError:
        return SECTOR_CATEGORIES.index("unknown")


def _dominant_sector_on_date(universe_stocks: dict[str, pd.DataFrame], target_date) -> str:
    """
    Best-effort dominant sector on target_date from universe price/volume.
    """
    if not universe_stocks:
        return "unknown"
    td = pd.Timestamp(target_date)
    sector_returns: dict[str, list[float]] = {c: [] for c in SECTOR_CATEGORIES}
    sector_volumes: dict[str, list[float]] = {c: [] for c in SECTOR_CATEGORIES}
    for tk, udf in universe_stocks.items():
        if tk.upper() == "IHSG":
            continue
        if udf is None or udf.empty:
            continue
        try:
            idx_loc = udf.index.get_loc(td, method="nearest")
            idx = int(idx_loc)
        except Exception:
            continue
        if idx <= 0 or idx >= len(udf):
            continue
        try:
            prev = float(udf.iloc[idx - 1].get("Close", 0) or 0)
            curr = float(udf.iloc[idx].get("Close", 0) or 0)
            vol = float(udf.iloc[idx].get("Volume", 0) or 0)
        except Exception:
            continue
        if prev <= 0 or curr <= 0:
            continue
        sector = SECTOR_MAP.get(tk.lower(), "unknown")
        sector_returns[sector].append(curr / prev - 1)
        sector_volumes[sector].append(vol)

    best_sector = "unknown"
    best_score = -1e9
    for sector, rets in sector_returns.items():
        if not rets:
            continue
        avg_ret = sum(rets) / len(rets)
        avg_vol = sum(sector_volumes.get(sector, [])) / max(len(sector_volumes.get(sector, [])), 1)
        score = avg_ret * 1000 + avg_vol
        if score > best_score:
            best_score = score
            best_sector = sector
    return best_sector




def get_historical_bandar_features(ticker: str, target_date) -> dict:
    """
    Query database to calculate Bandarmologi ratios (Top 3 concentration & retail ratio)
    for a given ticker up to target_date.
    """
    try:
        from db import SessionLocal
        from db.models import BrokerAccumulation
        import pandas as pd
        
        db = SessionLocal()
        try:
            # Query last 35 trading days of broker accumulation to cover rolling 30-day window
            accum_rows = db.query(BrokerAccumulation).filter(
                BrokerAccumulation.ticker == ticker,
                BrokerAccumulation.trade_date <= target_date
            ).order_by(BrokerAccumulation.trade_date.desc()).limit(1050).all() # limit to prevent huge queries
            
            if not accum_rows:
                return {}
                
            df_accum = pd.DataFrame([{
                "date": r.trade_date,
                "broker_code": r.broker_code,
                "buy_value": float(r.buy_value or 0),
                "sell_value": float(r.sell_value or 0),
            } for r in accum_rows])
            
            if df_accum.empty:
                return {}

            RETAIL_BROKERS = {"XL", "XC", "YP"}
            daily_list = []
            for dt, group in df_accum.groupby("date"):
                buy_vals = sorted(group["buy_value"].tolist(), reverse=True)
                total_buy = sum(buy_vals)
                top3_buy = sum(buy_vals[:3])
                
                sell_vals = sorted(group["sell_value"].tolist(), reverse=True)
                total_sell = sum(sell_vals)
                top3_sell = sum(sell_vals[:3])
                
                retail_buy = group[group["broker_code"].isin(RETAIL_BROKERS)]["buy_value"].sum()
                retail_sell = group[group["broker_code"].isin(RETAIL_BROKERS)]["sell_value"].sum()
                
                daily_list.append({
                    "date": dt,
                    "total_buy": total_buy,
                    "total_sell": total_sell,
                    "top3_buy": top3_buy,
                    "top3_sell": top3_sell,
                    "retail_buy": retail_buy,
                    "retail_sell": retail_sell,
                })
                
            df_daily = pd.DataFrame(daily_list).set_index("date").sort_index()
            
            # We want the values for target_date (last row)
            roll7 = df_daily.tail(7)
            t_buy7 = roll7["total_buy"].sum()
            t_sell7 = roll7["total_sell"].sum()
            
            roll30 = df_daily.tail(30)
            t_buy30 = roll30["total_buy"].sum()
            t_sell30 = roll30["total_sell"].sum()
            
            return {
                "top3_buy_ratio_7d": float(roll7["top3_buy"].sum() / t_buy7) if t_buy7 > 0 else 0.0,
                "top3_sell_ratio_7d": float(roll7["top3_sell"].sum() / t_sell7) if t_sell7 > 0 else 0.0,
                "retail_buy_ratio_7d": float(roll7["retail_buy"].sum() / t_buy7) if t_buy7 > 0 else 0.0,
                "retail_sell_ratio_7d": float(roll7["retail_sell"].sum() / t_sell7) if t_sell7 > 0 else 0.0,
                
                "top3_buy_ratio_1m": float(roll30["top3_buy"].sum() / t_buy30) if t_buy30 > 0 else 0.0,
                "top3_sell_ratio_1m": float(roll30["top3_sell"].sum() / t_sell30) if t_sell30 > 0 else 0.0,
            }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to calculate live bandar ratios for {ticker}: {e}")
        return {}

def extract_features(ticker: str, scores: dict, macro_data: dict, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Extract vector features for a single stock.
    Returns a single-row DataFrame.
    """
    ticker_scores = scores.get(ticker, {})
    bandarm = ticker_scores.get("bandarm", {})
    tech = ticker_scores.get("technical", {})
    fund = ticker_scores.get("fundamental", {})

    # 1. Bandar Features
    price_analysis = bandarm.get("price_analysis", {})
    from datetime import date
    bandar_ratios = get_historical_bandar_features(ticker, date.today())

    bandar_features = {
        "bandarm_score": bandarm.get("score", 5.0),
        "dist_avg_7d": _parse_pct(price_analysis.get("distance_from_7d")),
        "dist_avg_1m": _parse_pct(price_analysis.get("distance_from_1m")),
        "foreign_net_7d": _parse_number(bandarm.get("window_7d", {}).get("foreign_net_7d"), 0.0) / 1e9, # In Billions
        "foreign_net_1m": _parse_number(bandarm.get("window_1m", {}).get("foreign_net_1m"), 0.0) / 1e9,
        "top3_buy_ratio_7d": bandar_ratios.get("top3_buy_ratio_7d", 0.0),
        "top3_sell_ratio_7d": bandar_ratios.get("top3_sell_ratio_7d", 0.0),
        "retail_buy_ratio_7d": bandar_ratios.get("retail_buy_ratio_7d", 0.0),
        "retail_sell_ratio_7d": bandar_ratios.get("retail_sell_ratio_7d", 0.0),
        "top3_buy_ratio_1m": bandar_ratios.get("top3_buy_ratio_1m", 0.0),
        "top3_sell_ratio_1m": bandar_ratios.get("top3_sell_ratio_1m", 0.0),
        "is_retail_accum": 1.0 if "Penalty: Broker retail" in str(bandarm.get("data_used")) else 0.0,
    }

    # 2. Technical Features
    divergence = tech.get("divergence", {})
    data_used = tech.get("data_used", [])

    tech_features = {
        "technical_score": tech.get("score", 5.0),
        "rsi": _extract_first_numeric(data_used, "RSI:", 50.0),
        "is_bullish_trend": 1.0 if tech.get("trend") == "bullish" else 0.0 if tech.get("trend") == "bearish" else 0.5,
        "is_rsi_divergence": 1.0 if divergence.get("rsi") == "bullish" else -1.0 if divergence.get("rsi") == "bearish" else 0.0,
        "is_macd_divergence": 1.0 if divergence.get("macd") == "bullish" else -1.0 if divergence.get("macd") == "bearish" else 0.0,
        "vol_ratio": _extract_first_numeric(data_used, "Vol ratio", 1.0),
    }

    # 3. Macro Features
    macro_features = {
        "macro_score": _parse_number(macro_data.get("score"), 5.0),
        "ihsg_vs_ma20": _parse_number(macro_data.get("ihsg_vs_ma20"), 0.0),
        "usdidr_val": _parse_number(macro_data.get("usdidr"), 16000.0) / 1000, # Scaled
    }

    # 4. OHLCV Features (Recent Price Action)
    if ohlcv is not None and not ohlcv.empty:
        closes = pd.to_numeric(ohlcv["Close"], errors="coerce")
        highs = pd.to_numeric(ohlcv["High"], errors="coerce") if "High" in ohlcv else None
        lows = pd.to_numeric(ohlcv["Low"], errors="coerce") if "Low" in ohlcv else None
        volumes = pd.to_numeric(ohlcv["Volume"], errors="coerce") if "Volume" in ohlcv else None
        opens = pd.to_numeric(ohlcv["Open"], errors="coerce") if "Open" in ohlcv else None

        closes = closes.dropna()
        returns = closes.pct_change()
        ma20 = closes.rolling(20).mean()
        ma50 = closes.rolling(50).mean()

        current_price = float(closes.iloc[-1]) if len(closes) > 0 else 0.0
        support_near = _parse_number(tech.get("support_near"))
        resistance_near = _parse_number(tech.get("resistance_near"))

        volume_spike = 0.0
        if volumes is not None and len(volumes.dropna()) > 20:
            vol = volumes.dropna()
            volume_spike = float(vol.iloc[-1] / vol.tail(20).mean()) if vol.tail(20).mean() else 0.0

        range_pct = 0.0
        if highs is not None and lows is not None and len(highs.dropna()) > 0 and len(lows.dropna()) > 0 and current_price > 0:
            latest_high = float(highs.dropna().iloc[-1])
            latest_low = float(lows.dropna().iloc[-1])
            range_pct = (latest_high - latest_low) / current_price

        # Advanced Indicators
        macd, macd_hist = _compute_macd(closes)
        bb_upper, bb_lower = _compute_bb(closes)
        stoch_k, stoch_d = _compute_stoch(highs, lows, closes) if highs is not None and lows is not None else (closes*0, closes*0)
        atr = _compute_atr(highs, lows, closes) if highs is not None and lows is not None else closes*0

        price_features = {
            "ret_1d": returns.iloc[-1] if len(returns) > 1 else 0.0,
            "ret_3d": (closes.iloc[-1] / closes.iloc[-4] - 1) if len(closes) > 4 else 0.0,
            "ret_5d": (closes.iloc[-1] / closes.iloc[-6] - 1) if len(closes) > 6 else 0.0,
            "volatility_20d": returns.tail(20).std() if len(returns) > 20 else 0.0,
            "gap_open": (opens.dropna().iloc[-1] / closes.iloc[-2] - 1) if opens is not None and len(opens.dropna()) > 0 and len(closes) > 2 else 0.0,
            "ma_dist_20": (current_price / ma20.iloc[-1] - 1) if len(ma20.dropna()) > 0 and ma20.iloc[-1] else 0.0,
            "ma_dist_50": (current_price / ma50.iloc[-1] - 1) if len(ma50.dropna()) > 0 and ma50.iloc[-1] else 0.0,
            "volume_spike": volume_spike,
            "support_proximity": _proximity(current_price, support_near),
            "resistance_proximity": _proximity(current_price, resistance_near),
            "range_pct": range_pct,
            "macd": float(macd.iloc[-1] / current_price) if len(macd.dropna()) > 0 and current_price > 0 else 0.0,
            "macd_hist": float(macd_hist.iloc[-1] / current_price) if len(macd_hist.dropna()) > 0 and current_price > 0 else 0.0,
            "bb_upper_dist": float(current_price / bb_upper.iloc[-1] - 1) if len(bb_upper.dropna()) > 0 else 0.0,
            "bb_lower_dist": float(current_price / bb_lower.iloc[-1] - 1) if len(bb_lower.dropna()) > 0 else 0.0,
            "stoch_k": float(stoch_k.iloc[-1]) if len(stoch_k.dropna()) > 0 else 0.0,
            "stoch_d": float(stoch_d.iloc[-1]) if len(stoch_d.dropna()) > 0 else 0.0,
            "atr": float(atr.iloc[-1] / current_price) if len(atr.dropna()) > 0 and current_price > 0 else 0.0,
        }
    else:
        price_features = {f"ret_{i}d": 0.0 for i in [1, 3, 5]}
        price_features.update({
            "volatility_20d": 0.0,
            "gap_open": 0.0,
            "ma_dist_20": 0.0,
            "ma_dist_50": 0.0,
            "volume_spike": 0.0,
            "support_proximity": 0.0,
            "resistance_proximity": 0.0,
            "range_pct": 0.0,
            "macd": 0.0,
            "macd_hist": 0.0,
            "bb_upper_dist": 0.0,
            "bb_lower_dist": 0.0,
            "stoch_k": 0.0,
            "stoch_d": 0.0,
            "atr": 0.0,
        })

    # Combine all
    all_features = {**bandar_features, **tech_features, **macro_features, **price_features}
    for col in FEATURE_COLUMNS:
        all_features.setdefault(col, 0.0)
    row = pd.DataFrame([all_features])[FEATURE_COLUMNS]
    return row.fillna(0.0)

def prepare_training_data(ohlcv: pd.DataFrame, ticker: str = None, universe_ohlcv: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate historical features and targets from OHLCV for training.
    If ticker is provided, retrieves historical Bandarmologi and Agent scores from DB.
    Returns (features_df, targets_df) where targets_df contains columns for 1d, 3d, 5d, and 7d horizons.
    """
    df = ohlcv.copy()
    
    # Ensure index is datetime and sorted
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Targets: Future returns for 1d, 3d, 5d, 7d
    df['target_1d'] = df['Close'].shift(-1) / df['Close'] - 1
    df['target_3d'] = df['Close'].shift(-3) / df['Close'] - 1
    df['target_5d'] = df['Close'].shift(-5) / df['Close'] - 1
    df['target_7d'] = df['Close'].shift(-7) / df['Close'] - 1

    # Simple Technical Features for History
    df['ret_1d'] = df['Close'].pct_change()
    df['ret_3d'] = df['Close'].pct_change(3)
    df['ret_5d'] = df['Close'].pct_change(5)
    df['volatility_20d'] = df['ret_1d'].rolling(20).std()

    # Moving Average distances
    df['ma20'] = df['Close'].rolling(20).mean()
    df['ma50'] = df['Close'].rolling(50).mean()
    df['ma_dist_20'] = df['Close'] / df['ma20'] - 1
    df['ma_dist_50'] = df['Close'] / df['ma50'] - 1
    
    # Calculate RSI and Trend historically
    df['rsi'] = _compute_rsi(df['Close'], 14)
    df['is_bullish_trend'] = (df['ma20'] > df['ma50']).astype(float)
    
    # Volume Ratio historical
    vol_ma20 = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / vol_ma20
    
    # Additional OHLCV-derived features for Day-1 parity
    df['volume_spike'] = df['Volume'] / vol_ma20
    df['range_pct'] = (df['High'] - df['Low']) / df['Close']
    df['gap_open'] = df['Open'] / df['Close'].shift(1) - 1

    # Advanced Indicators
    macd, macd_hist = _compute_macd(df['Close'])
    bb_upper, bb_lower = _compute_bb(df['Close'])
    stoch_k, stoch_d = _compute_stoch(df['High'], df['Low'], df['Close'])
    atr = _compute_atr(df['High'], df['Low'], df['Close'])

    df['macd'] = macd / df['Close']
    df['macd_hist'] = macd_hist / df['Close']
    df['bb_upper_dist'] = df['Close'] / bb_upper - 1
    df['bb_lower_dist'] = df['Close'] / bb_lower - 1
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    df['atr'] = atr / df['Close']

    # ── Volume profile / orderbook-proxy from OHLCV ─────────────────────
    roll20 = df.rolling(20, min_periods=10)
    price_min20 = roll20['Low'].min()
    price_max20 = roll20['High'].max()
    price_range20 = (price_max20 - price_min20).replace(0, np.nan)

    # VWAP approx from today-style cumulative TP * Volume / ΣVolume over 20d(window)
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    vwap20 = (tp * df['Volume']).rolling(20, min_periods=10).sum() / df['Volume'].rolling(20, min_periods=10).sum().replace(0, np.nan)
    df['vwap_deviation_20d'] = (df['Close'] / vwap20 - 1).fillna(0.0)

    # Volume segmented by relative price bucket inside each day: upper/mid/lower 33%
    upper = (df['High'] - (df['High'] + df['Low'] + df['Close']) / 3.0).clip(lower=0)
    lower = ((df['High'] + df['Low'] + df['Close']) / 3.0 - df['Low']).clip(lower=0)
    mid = df['Volume'] - upper - lower
    df['ob_imbalance_proxy_20d'] = ((upper - lower) / df['Volume'].replace(0, np.nan)).rolling(20, min_periods=10).mean().fillna(0.0)
    df['signed_volume_20d'] = (df['ret_1d'] * df['Volume']).rolling(20, min_periods=10).sum().fillna(0.0)

    # Range concentration: how much of 20d range is consumed by recent 5d high-low
    h5 = df['High'].rolling(5, min_periods=3).max()
    l5 = df['Low'].rolling(5, min_periods=3).min()
    df['range_concentration_20d'] = ((h5 - l5) / price_range20).fillna(0.0)

    # Volume-at-band: share of 20d volume when price in upper/mid/lower 3rd of 20d range
    close_pos = (df['Close'] - price_min20) / price_range20
    up_mask = (close_pos >= 0.66)
    mid_mask = (close_pos >= 0.33) & (close_pos < 0.66)
    low_mask = (close_pos < 0.33)
    vol_up = (df['Volume'] * up_mask.astype(int)).rolling(20, min_periods=10).sum()
    vol_mid = (df['Volume'] * mid_mask.astype(int)).rolling(20, min_periods=10).sum()
    vol_low = (df['Volume'] * low_mask.astype(int)).rolling(20, min_periods=10).sum()
    vol_sum20 = df['Volume'].rolling(20, min_periods=10).sum().replace(0, np.nan)
    df['vol_profile_20d_upper'] = (vol_up / vol_sum20).fillna(0.0)
    df['vol_profile_20d_mid'] = (vol_mid / vol_sum20).fillna(0.0)
    df['vol_profile_20d_lower'] = (vol_low / vol_sum20).fillna(0.0)

    # ── Day-1 Specific Features ──────────────────────────────────────────────
    # Intraday candle structure
    candle_range = (df['High'] - df['Low']).replace(0, np.nan)
    df['close_to_high'] = (df['High'] - df['Close']) / df['Close']   # upper wick ratio
    df['close_to_low'] = (df['Close'] - df['Low']) / df['Close']     # lower wick (bullish if big)
    df['body_ratio'] = (df['Close'] - df['Open']).abs() / candle_range.fillna(1e-8)  # body vs full range

    # Mean-reversion z-score of daily return
    ret_mean = df['ret_1d'].rolling(20).mean()
    ret_std = df['ret_1d'].rolling(20).std().replace(0, np.nan)
    df['ret_1d_zscore'] = (df['ret_1d'] - ret_mean) / ret_std  # negative = oversold bounce signal

    # Short-term volume trend (accelerating vs decelerating)
    df['vol_trend_5d'] = df['Volume'].rolling(5).mean() / vol_ma20

    # Day-of-week (Senin=0, Jumat=4) — market anomaly effect
    df['day_of_week'] = pd.to_datetime(df.index).dayofweek.astype(float)

    # Gap continuation: gap size × previous day return direction
    df['gap_continuation'] = df['gap_open'] * df['ret_1d'].shift(1)

    # Longer return horizons
    df['ret_2d'] = df['Close'].pct_change(2)
    df['ret_10d'] = df['Close'].pct_change(10)

    # Lagged RSI (1-day lag to avoid lookahead on same-day signal)
    rsi_series = _compute_rsi(df['Close'], 14)
    df['rsi_14_prev'] = rsi_series.shift(1)

    # Lagged volume spike
    df['volume_spike_prev'] = df['volume_spike'].shift(1)

    # ── IHSG Market Context Features ──────────────────────────────────────
    ihsg_df = _fetch_ihsg_history()
    if ihsg_df is not None and not ihsg_df.empty:
        # Compute IHSG indicators
        ihsg_ret_1d = ihsg_df['close'].pct_change()
        ihsg_ret_5d = ihsg_df['close'].pct_change(5)
        ihsg_rsi = _compute_rsi(ihsg_df['close'], 14)
        ihsg_ma20 = ihsg_df['close'].rolling(20).mean()
        ihsg_ma50 = ihsg_df['close'].rolling(50).mean()
        ihsg_ma_dist_20 = ihsg_df['close'] / ihsg_ma20 - 1
        ihsg_volatility = ihsg_ret_1d.rolling(20).std()
        ihsg_trend = (ihsg_ma20 > ihsg_ma50).astype(float)

        ihsg_features = pd.DataFrame({
            'ihsg_ret_1d': ihsg_ret_1d,
            'ihsg_ret_5d': ihsg_ret_5d,
            'ihsg_rsi': ihsg_rsi,
            'ihsg_ma_dist_20': ihsg_ma_dist_20,
            'ihsg_volatility': ihsg_volatility,
            'ihsg_trend': ihsg_trend,
        }, index=ihsg_df.index)

        # Join on date index
        df = df.join(ihsg_features, how='left')

        # Relative strength: stock return vs IHSG return
        df['stock_vs_ihsg_1d'] = df['ret_1d'] - df['ihsg_ret_1d'].fillna(0)
    else:
        for col in ['ihsg_ret_1d', 'ihsg_ret_5d', 'ihsg_rsi', 'ihsg_ma_dist_20',
                     'ihsg_volatility', 'ihsg_trend', 'stock_vs_ihsg_1d']:
            df[col] = 0.0

    # Fetch from database if ticker is provided
    db_scores = None
    db_accum = None
    if ticker:
        try:
            from db import SessionLocal
            from db.models import AgentScore, BrokerAccumulation
            
            db = SessionLocal()
            try:
                # 1. Agent scores
                scores_rows = db.query(AgentScore).filter_by(ticker=ticker).all()
                if scores_rows:
                    db_scores = pd.DataFrame([{
                        "date": pd.to_datetime(r.run_date),
                        "bandarm_score": float(r.bandarm_score or 5.0),
                        "technical_score": float(r.technical_score or 5.0),
                        "macro_score": 5.0 if r.macro_signal == "UNKNOWN" else 8.0 if r.macro_signal == "BULLISH" else 3.0,
                    } for r in scores_rows]).set_index("date")
                
                # 2. Broker accumulation
                accum_rows = db.query(BrokerAccumulation).filter_by(ticker=ticker).all()
                if accum_rows:
                    df_accum = pd.DataFrame([{
                        "date": pd.to_datetime(r.trade_date),
                        "buy_lot": float(r.buy_lot or 0),
                        "buy_value": float(r.buy_value or 0),
                        "day_foreign_net": float(r.day_foreign_net or 0)
                    } for r in accum_rows])
                    
                    df_daily = df_accum.groupby("date").agg({
                        "buy_lot": "sum",
                        "buy_value": "sum",
                        "day_foreign_net": "first"
                    }).sort_index()
                    
                    # Compute rolling sums on the daily grouped accumulation
                    roll7_val = df_daily["buy_value"].rolling(7).sum()
                    roll7_lot = df_daily["buy_lot"].rolling(7).sum()
                    df_daily["avg_7d"] = roll7_val / (roll7_lot * 100)
                    
                    roll30_val = df_daily["buy_value"].rolling(30).sum()
                    roll30_lot = df_daily["buy_lot"].rolling(30).sum()
                    df_daily["avg_1m"] = roll30_val / (roll30_lot * 100)
                    
                    df_daily["foreign_net_7d"] = df_daily["day_foreign_net"].rolling(7).sum() / 1e9
                    df_daily["foreign_net_1m"] = df_daily["day_foreign_net"].rolling(30).sum() / 1e9
                    
                    db_accum = df_daily[["avg_7d", "avg_1m", "foreign_net_7d", "foreign_net_1m"]]
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to fetch historical features from DB for {ticker}: {e}")

    # Merge Database Features
    if db_scores is not None:
        df = df.join(db_scores, how="left")
    if db_accum is not None:
        df = df.join(db_accum, how="left")
        
        # Calculate distances based on merged rolling averages
        df["dist_avg_7d"] = ((df["Close"] - df["avg_7d"]) / df["avg_7d"] * 100).fillna(0.0)
        df["dist_avg_1m"] = ((df["Close"] - df["avg_1m"]) / df["avg_1m"] * 100).fillna(0.0)

    # ── Sector context features from universe OHLCV ───────────────────────
    sector_today_defaults = {
        "ticker_sector_id": float(_get_sector_id(SECTOR_MAP.get(ticker.lower() if ticker else "", "unknown"))),
        "dominant_sector_id": float(_get_sector_id("unknown")),
        "dominant_sector_ret_1d": 0.0,
        "dominant_sector_ret_5d": 0.0,
        "stock_vs_sector_1d": 0.0,
        "stock_vs_sector_5d": 0.0,
        "sector_strength_vs_ihsg": 0.0,
    }
    if universe_ohlcv:
        try:
            def_sector = "unknown"
            ticker_sector = SECTOR_MAP.get(ticker.lower() if ticker else "", "unknown")
            sector_today_defaults["ticker_sector_id"] = float(_get_sector_id(ticker_sector))
            td = pd.Timestamp(df.index[-1])
            dom_sector = _dominant_sector_on_date(universe_ohlcv, td)
            if dom_sector not in (None, "", "unknown"):
                def_sector = dom_sector
            dom_id = _get_sector_id(def_sector)
            sector_today_defaults["dominant_sector_id"] = float(dom_id)

            def _sector_ret(sector_name: str, window: int) -> float:
                vals = []
                for tk, udf in universe_ohlcv.items():
                    if tk.upper() == "IHSG":
                        continue
                    if SECTOR_MAP.get(tk.lower(), "unknown") != sector_name:
                        continue
                    if udf is None or udf.empty:
                        continue
                    try:
                        idx = udf.index.get_loc(td, method="nearest")
                        idx = int(idx)
                    except Exception:
                        continue
                    if idx - window < 0 or idx >= len(udf):
                        continue
                    try:
                        prev = float(udf.iloc[idx - window].get("Close", 0) or 0)
                        curr = float(udf.iloc[idx].get("Close", 0) or 0)
                    except Exception:
                        continue
                    if prev > 0 and curr > 0:
                        vals.append(curr / prev - 1)
                return float(sum(vals) / len(vals)) if vals else 0.0

            prev_idx = min(len(df) - 1, max(0, len(df) - 2))
            prev_td = pd.Timestamp(df.index[prev_idx])
            s1d = _sector_ret(def_sector, 1)
            s5d = _sector_ret(def_sector, 5)
            sector_today_defaults["dominant_sector_ret_1d"] = s1d
            sector_today_defaults["dominant_sector_ret_5d"] = s5d
            sector_today_defaults["stock_vs_sector_1d"] = float(df.iloc[prev_idx]["ret_1d"]) - s1d
            sector_today_defaults["stock_vs_sector_5d"] = float((df.iloc[-1]["Close"] / df.iloc[max(0, len(df)-6)]["Close"] - 1)) - s5d

            ihsg_ret5 = 0.0
            if "ihsg_ret_5d" in df.columns:
                ihsg_ret5 = float(df.iloc[prev_idx]["ihsg_ret_5d"]) if pd.notna(df.iloc[prev_idx].get("ihsg_ret_5d", 0)) else 0.0
            sector_today_defaults["sector_strength_vs_ihsg"] = s5d - ihsg_ret5
        except Exception as e:
            logger.warning(f"Failed to compute sector features for {ticker}: {e}")

    for col, val in sector_today_defaults.items():
        df[col] = val

    # Fill default baseline values for missing DB features
    df["bandarm_score"] = df.get("bandarm_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["technical_score"] = df.get("technical_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["macro_score"] = df.get("macro_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["dist_avg_7d"] = df.get("dist_avg_7d", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["dist_avg_1m"] = df.get("dist_avg_1m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["foreign_net_7d"] = df.get("foreign_net_7d", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["foreign_net_1m"] = df.get("foreign_net_1m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["is_retail_accum"] = df.get("is_retail_accum", pd.Series(0.0, index=df.index)).fillna(0.0)

    # Foreign flow z-score
    fn7 = df["foreign_net_7d"]
    fn_mean = fn7.rolling(20).mean()
    fn_std = fn7.rolling(20).std().replace(0, np.nan)
    df["foreign_flow_zscore"] = ((fn7 - fn_mean) / fn_std).fillna(0.0)

    # Ticker categorical id so the model can share signal across stocks
    df["ticker_id"] = 0 if not ticker else (_ticker_id(ticker))

    # Drop rows with NaN (from rolling/shifting of targets and indicators)
    df = df.dropna(subset=['target_1d', 'target_3d', 'target_5d', 'target_7d'])

    # Ensure all columns in FEATURE_COLUMNS exist
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    targets = df[['target_1d', 'target_3d', 'target_5d', 'target_7d']]
    return df[FEATURE_COLUMNS], targets
