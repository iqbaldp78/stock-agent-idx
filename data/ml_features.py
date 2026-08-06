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
    "day_foreign_net",
    "frequency_1d",
    "close_vs_avg",
    "top3_buy_ratio_7d",
    "top3_sell_ratio_7d",
    "retail_buy_ratio_7d",
    "retail_sell_ratio_7d",
    "top3_buy_ratio_1m",
    "top3_sell_ratio_1m",
    "is_retail_accum",
    "dominance_score",
    "haka_score",
    "is_fomo_trap",
    "rsi",
    "is_bullish_trend",
    "vol_ratio",
    "ret_1d",
    "ret_1d_lag1",
    "ret_1d_lag2",
    "ret_1d_lag3",
    "ret_1d_lag4",
    "ret_1d_lag5",
    "ret_3d",
    "ret_5d",
    "volatility_10d",
    "volatility_20d",
    "gap_open",
    "ma_dist_5",
    "ma_dist_20",
    "ma_dist_50",
    "ma_dist_200",
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
    # Brainstorm features
    "news_score",
    "commodity_score",
    "bandar_accum_ratio",
    "ihsg_trend_3d",
    # Candlestick pattern features
    "candlestick_winrate",
    "is_bullish_pattern",
    "is_bearish_pattern",
    # Report vs News Sentiment & Count features (7d & 30d)
    "report_sent_7d",
    "report_sent_30d",
    "report_count_7d",
    "report_count_30d",
    "news_sent_7d",
    "news_sent_30d",
    "news_count_7d",
    "news_count_30d",
]

# Kolom yang benar-benar digunakan untuk melatih ML (hanya yang bisa dihitung secara historis)
ML_TRAIN_FEATURES = [
    # ── Proven useful (importance > 0) ──────────────────────────────────
    "foreign_net_7d",
    "foreign_net_1m",
    "day_foreign_net",
    "frequency_1d",
    "close_vs_avg",
    "rsi",
    "is_bullish_trend",
    "vol_ratio",
    "ret_1d",
    "ret_1d_lag1",
    "ret_1d_lag2",
    "ret_1d_lag3",
    "ret_1d_lag4",
    "ret_1d_lag5",
    "ret_3d",
    "ret_5d",
    "volatility_10d",
    "volatility_20d",
    "gap_open",
    "ma_dist_5",
    "ma_dist_20",
    "ma_dist_50",
    "ma_dist_200",
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
    # Brainstorm features
    "bandar_accum_ratio",
    # Candlestick pattern features
    "candlestick_winrate",
    "is_bullish_pattern",
    "is_bearish_pattern",
]

def _pick_col(df: pd.DataFrame, name: str) -> str | None:
    """
    Cari kolom secara case-insensitive, kembalikan nama aslinya (atau None).
    Dipakai agar fitur tidak diam-diam jadi 0 hanya karena beda kapitalisasi
    nama kolom antar sumber data (Stockbit vs yfinance vs hasil normalisasi).
    """
    target = name.strip().lower()
    for col in df.columns:
        if str(col).strip().lower() == target:
            return col
    return None


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
        logger.warning(f"Failed to fetch IHSG history from DB: {e}")
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


def _proximity(price: float, level: float) -> float:
    """Hitung seberapa dekat harga ke level support/resistance.
    Return: nilai mendekati 0 = sangat dekat, negatif = harga di bawah level.
    """
    if not level or level == 0:
        return 0.0
    return float((price - level) / level)


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

def fetch_news_report_features(ticker: str) -> dict:
    """
    Mengambil fitur sentimen dan jumlah dokumen terpisah untuk 'report' vs 'news' 
    dalam rentang 7 hari dan 30 hari dari tabel news_signals.
    """
    from datetime import datetime
    import numpy as np
    defaults = {
        "report_sent_7d": 5.0,
        "report_sent_30d": 5.0,
        "report_count_7d": 0.0,
        "report_count_30d": 0.0,
        "news_sent_7d": 5.0,
        "news_sent_30d": 5.0,
        "news_count_7d": 0.0,
        "news_count_30d": 0.0,
    }
    if not ticker:
        return defaults
    from db.vector_db import get_news_sentiment_features
    
    defaults = {
        "report_sent_7d": 5.0,
        "report_sent_30d": 5.0,
        "report_count_7d": 0.0,
        "report_count_30d": 0.0,
        "news_sent_7d": 5.0,
        "news_sent_30d": 5.0,
        "news_count_7d": 0.0,
        "news_count_30d": 0.0,
    }
    if not ticker:
        return defaults
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Ambil data dari Vector DB
        df = get_news_sentiment_features(ticker.upper(), start_date.isoformat(), end_date.isoformat())
        
        if df.empty:
            return defaults
            
        # Hitung untuk 7d dan 30d
        now = datetime.now()
        
        def agg_stats(days):
            mask = df.index >= (now - timedelta(days=days))
            subset = df[mask]
            if subset.empty:
                return 5.0, 0.0
            avg_sent = subset['avg_sentiment'].mean()
            count = subset['news_count'].sum()
            return avg_sent, count

        news_sent_7d, news_count_7d = agg_stats(7)
        news_sent_30d, news_count_30d = agg_stats(30)
        
        return {
            "report_sent_7d": 5.0,
            "report_sent_30d": 5.0,
            "report_count_7d": 0.0,
            "report_count_30d": 0.0,
            "news_sent_7d": news_sent_7d,
            "news_sent_30d": news_sent_30d,
            "news_count_7d": news_count_7d,
            "news_count_30d": news_count_30d,
        }
    except Exception as e:
        logger.warning(f"Error fetching news/report features for {ticker}: {e}")
        return defaults


def extract_features(ticker: str, scores: dict, macro_data: dict, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Extract vector features for a single stock.
    Returns a single-row DataFrame.
    
    FIXED (Fase 0B): Now computes all missing features that training uses:
    - IHSG context (ihsg_ret_1d/5d, ihsg_rsi, ihsg_ma_dist_20, ihsg_volatility, ihsg_trend, stock_vs_ihsg_1d)
    - Day-of-week
    - Lag returns (ret_1d_lag1..5, ret_2d, ret_10d)
    - Additional volatility & technical (volatility_10d, ret_1d_zscore, vol_trend_5d, close_to_high/low)
    """
    from datetime import date, datetime
    import numpy as np
    
    ticker_scores = scores.get(ticker, {})
    bandarm = ticker_scores.get("bandarm", {})
    tech = ticker_scores.get("technical", {})
    fund = ticker_scores.get("fundamental", {})

    news_report_feats = fetch_news_report_features(ticker)

    # 1. Bandar Features
    price_analysis = bandarm.get("price_analysis", {})
    bandar_ratios = get_historical_bandar_features(ticker, date.today())

    # CATATAN: day_foreign_net, foreign_net_7d/1m, foreign_flow_zscore, frequency_1d,
    # dan close_vs_avg SENGAJA tidak diambil dari JSON agent di sini.
    # Training menghitungnya dari kolom NetForeign/Frequency/AveragePrice di OHLCV,
    # dan data yang sama tersedia di live (graph/workflow.py memakai
    # data.fetcher_stockbit.get_ohlcv yang mengembalikan kolom-kolom itu).
    # Mengambilnya dari agent berarti dua sumber berbeda untuk fitur bernama sama.
    # Sekarang semuanya dari compute_ohlcv_features().
    bandar_features = {
        "bandarm_score": bandarm.get("score", 5.0),
        "dist_avg_7d": _parse_pct(price_analysis.get("distance_from_7d")),
        "dist_avg_1m": _parse_pct(price_analysis.get("distance_from_1m")),
        "top3_buy_ratio_7d": bandar_ratios.get("top3_buy_ratio_7d", 0.0),
        "top3_sell_ratio_7d": bandar_ratios.get("top3_sell_ratio_7d", 0.0),
        "retail_buy_ratio_7d": bandar_ratios.get("retail_buy_ratio_7d", 0.0),
        "retail_sell_ratio_7d": bandar_ratios.get("retail_sell_ratio_7d", 0.0),
        "top3_buy_ratio_1m": bandar_ratios.get("top3_buy_ratio_1m", 0.0),
        "top3_sell_ratio_1m": bandar_ratios.get("top3_sell_ratio_1m", 0.0),
        "is_retail_accum": 1.0 if bandar_ratios.get("is_retail_accum", False) else 0.0,
        "dominance_score": 1.0 if bandarm.get("insight_dominance", {}).get("type") == "driver" else (-1.0 if bandarm.get("insight_dominance", {}).get("type") == "risk" else 0.0),
        "haka_score": 1.0 if bandarm.get("insight_aggressiveness", {}).get("type") == "driver" else (-1.0 if bandarm.get("insight_aggressiveness", {}).get("type") == "risk" else 0.0),
        "is_fomo_trap": 1.0 if bandarm.get("insight_fomo_trap", {}).get("type") == "risk" else 0.0,
    }
    # bandar_accum_ratio diisi setelah price_features tersedia (butuh foreign_net_1m
    # dari OHLCV), memakai helper bersama _bandar_accum_ratio().

    # 2. Technical Features (from agent scores)
    divergence = tech.get("divergence", {})

    # rsi, is_bullish_trend, dan vol_ratio SENGAJA tidak lagi diambil dari sini.
    # Dulu ketiganya diparse dari teks bebas di tech["data_used"] (mis. "RSI: 62.1")
    # dengan default 50.0 / 1.0 / 0.5 kalau formatnya tidak cocok — sementara
    # training menghitungnya dari OHLCV. Beda definisi, dan kegagalan parse tidak
    # pernah memunculkan error. Sekarang ketiganya datang dari
    # compute_ohlcv_features() seperti di training.
    tech_features = {
        "technical_score": tech.get("score", 5.0),
        "is_rsi_divergence": 1.0 if divergence.get("rsi") == "bullish" else -1.0 if divergence.get("rsi") == "bearish" else 0.0,
        "is_macd_divergence": 1.0 if divergence.get("macd") == "bullish" else -1.0 if divergence.get("macd") == "bearish" else 0.0,
    }

    # 3. Macro Features (from agent scores)
    macro_features = {
        "macro_score": _parse_number(macro_data.get("score"), 5.0),
        "ihsg_vs_ma20": _parse_number(macro_data.get("ihsg_vs_ma20"), 0.0),
        "usdidr_val": _parse_number(macro_data.get("usdidr"), 16000.0) / 1000, # Scaled
    }

    # 4. Fitur turunan data pasar (OHLCV + konteks IHSG)
    #
    # Dihitung oleh fungsi yang SAMA dengan yang dipakai training, lalu diambil
    # baris terakhirnya. Sebelumnya blok ini adalah implementasi kedua yang
    # terpisah, dan 13 fitur diam-diam melenceng definisinya dari versi training.
    #
    # Efek sampingnya: rsi, vol_ratio, dan is_bullish_trend di atas TIDAK lagi
    # dipakai — nilainya kini dihitung dari OHLCV, bukan diparse dari teks agent
    # (yang diam-diam jatuh ke default 50.0 / 1.0 / 0.5 kalau formatnya berubah).
    price_features = {}
    if ohlcv is not None and not ohlcv.empty:
        try:
            market = compute_ohlcv_features(
                ohlcv, ihsg=_fetch_ihsg_history(), ticker=ticker
            )
            if len(market):
                price_features = market.iloc[-1].to_dict()
        except Exception as e:
            logger.warning(f"compute_ohlcv_features gagal untuk {ticker}: {e}")
    else:
        logger.warning(f"{ticker}: OHLCV kosong — seluruh fitur pasar jatuh ke 0.0")

    # Support/resistance proximity tetap dari agent: levelnya berasal dari analisis
    # agent teknikal, bukan turunan OHLCV. (Tidak ada di ML_TRAIN_FEATURES.)
    current_price = 0.0
    try:
        closes_live = pd.to_numeric(ohlcv["Close"], errors="coerce").dropna()
        current_price = float(closes_live.iloc[-1]) if len(closes_live) else 0.0
    except Exception:
        pass
    price_features["support_proximity"] = _proximity(current_price, _parse_number(tech.get("support_near")))
    price_features["resistance_proximity"] = _proximity(current_price, _parse_number(tech.get("resistance_near")))

    # Candlestick dari agent dipakai HANYA kalau compute_ohlcv_features tidak
    # menghasilkannya (mis. OHLCV kosong), supaya definisinya tetap satu.
    candlestick_patterns = tech.get("candlestick_patterns", [])
    if candlestick_patterns and not price_features.get("candlestick_winrate"):
        price_features["candlestick_winrate"] = float(
            max([p.get("win_rate_bei", 0.5) for p in candlestick_patterns], default=0.5)
        )
        price_features["is_bullish_pattern"] = 1.0 if any(
            p.get("signal") in ["BULLISH", "STRONG BULLISH"] for p in candlestick_patterns
        ) else 0.0
        price_features["is_bearish_pattern"] = 1.0 if any(
            p.get("signal") == "BEARISH" for p in candlestick_patterns
        ) else 0.0

    # bandar_accum_ratio memakai helper bersama: foreign_net_1m dari OHLCV,
    # dist_avg_1m dari agent/DB. Satu definisi untuk kedua jalur.
    bandar_features["bandar_accum_ratio"] = _bandar_accum_ratio(
        float(price_features.get("foreign_net_1m", 0.0) or 0.0),
        float(bandar_features.get("dist_avg_1m", 0.0) or 0.0),
    )

    # Combine all
    # ihsg_features sudah tidak ada sebagai dict terpisah: fitur konteks IHSG kini
    # bagian dari price_features karena dihitung di compute_ohlcv_features().
    all_features = {**bandar_features, **tech_features, **macro_features, **price_features, **news_report_feats}
    for col in FEATURE_COLUMNS:
        all_features.setdefault(col, 0.0)
    row = pd.DataFrame([all_features])[FEATURE_COLUMNS]
    return row.fillna(0.0)

# ─── Satu Sumber Kebenaran untuk Fitur Turunan Data Pasar ───────────────────
#
# Fitur di daftar ini HANYA didefinisikan di compute_ohlcv_features().
# prepare_training_data() memakai seluruh frame; extract_features() memakai
# baris terakhir. Jangan pernah menghitung ulang salah satunya di tempat lain.
#
# Alasannya konkret: sebelum ini training dan live inference punya dua
# implementasi terpisah, dan 13 fitur diam-diam melenceng — vol_trend_5d beda
# skala ~200x (rasio volume vs selisih volatilitas), close_to_high terbalik
# tanda, rsi/vol_ratio/is_bullish_trend di live diparse dari teks agent, dan
# fitur foreign di live diambil dari JSON agent padahal training memakai kolom
# NetForeign. Bug kelas ini tidak pernah memunculkan error — hanya prediksi
# yang salah dengan tenang. Dijaga oleh scripts/check_feature_parity.py.
OHLCV_DERIVED_FEATURES = [
    # Return & lag
    "ret_1d", "ret_1d_lag1", "ret_1d_lag2", "ret_1d_lag3", "ret_1d_lag4", "ret_1d_lag5",
    "ret_2d", "ret_3d", "ret_5d", "ret_10d",
    # Volatilitas
    "volatility_10d", "volatility_20d", "ret_1d_zscore", "atr",
    # MA & tren
    "ma_dist_5", "ma_dist_20", "ma_dist_50", "ma_dist_200", "is_bullish_trend",
    # Indikator
    "rsi", "rsi_14_prev", "macd", "macd_hist",
    "bb_upper_dist", "bb_lower_dist", "stoch_k", "stoch_d",
    # Volume
    "vol_ratio", "volume_spike", "volume_spike_prev", "vol_trend_5d",
    # Struktur candle
    "close_to_high", "close_to_low", "body_ratio", "range_pct",
    "gap_open", "gap_continuation", "day_of_week",
    # Volume profile / orderbook proxy
    "vol_profile_20d_upper", "vol_profile_20d_mid", "vol_profile_20d_lower",
    "vwap_deviation_20d", "signed_volume_20d", "ob_imbalance_proxy_20d",
    "range_concentration_20d",
    # Candlestick
    "candlestick_winrate", "is_bullish_pattern", "is_bearish_pattern",
    # Metadata Stockbit (Frequency / NetForeign / AveragePrice)
    "day_foreign_net", "foreign_net_7d", "foreign_net_1m", "foreign_flow_zscore",
    "frequency_1d", "close_vs_avg",
    # Konteks IHSG
    "ihsg_ret_1d", "ihsg_ret_5d", "ihsg_rsi", "ihsg_ma_dist_20",
    "ihsg_volatility", "ihsg_trend", "ihsg_trend_3d", "stock_vs_ihsg_1d",
]


# Baris OHLCV minimum agar SEMUA fitur di OHLCV_DERIVED_FEATURES bisa dihitung.
# Ditentukan oleh window terpanjang: ma200. Pemanggil live inference WAJIB
# mengambil setidaknya sebanyak ini, kalau tidak ma_dist_200 diam-diam jadi 0.0
# sementara di training nilainya nyata.
MIN_HISTORY_ROWS = 200


def _bandar_accum_ratio(foreign_net_1m, dist_avg_1m):
    """
    Satu definisi bandar_accum_ratio, dipakai training (Series) maupun live (skalar).

    Tidak masuk compute_ohlcv_features() karena mencampur dua sumber:
    foreign_net_1m dari kolom NetForeign, dist_avg_1m dari tabel BrokerAccumulation.
    """
    if hasattr(foreign_net_1m, "astype"):
        return ((foreign_net_1m > 0) & (dist_avg_1m < 5.0)).astype(float)
    return float(foreign_net_1m > 0 and dist_avg_1m < 5.0)


def compute_ohlcv_features(ohlcv: pd.DataFrame, ihsg: pd.DataFrame | None = None,
                           ticker: str | None = None) -> pd.DataFrame:
    """
    Hitung semua fitur turunan data pasar — satu baris per tanggal.

    SATU-SATUNYA definisi untuk fitur di OHLCV_DERIVED_FEATURES. Vectorized supaya
    bisa dipakai dua jalur sekaligus:
      - training  : prepare_training_data() memakai seluruh frame
      - inference : extract_features() memakai .iloc[-1]

    Args:
        ohlcv : DataFrame ber-index tanggal dengan Open/High/Low/Close/Volume.
                Kolom opsional Frequency/NetForeign/AveragePrice (ada di Stockbit,
                tidak ada di fallback yfinance) dicocokkan case-insensitive.
        ihsg  : OHLCV IHSG untuk fitur konteks pasar; None -> fitur IHSG jadi 0.
        ticker: hanya untuk pesan log.

    Returns:
        DataFrame ber-index sama dengan `ohlcv`, berisi kolom OHLCV_DERIVED_FEATURES.
    """
    tag = ticker or "?"
    df = ohlcv.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    out = pd.DataFrame(index=df.index)

    # Window terpanjang yang dipakai fungsi ini adalah 200 hari (ma_dist_200).
    # Kalau input lebih pendek, fitur itu jadi NaN lalu diisi 0.0 — nilai yang
    # TAMPAK sah ("harga tepat di MA200") padahal artinya "tidak diketahui".
    # Di training window-nya panjang sehingga nilainya nyata, jadi input pendek
    # di live inference menghasilkan train/serve skew yang tidak terlihat.
    if len(df) < MIN_HISTORY_ROWS:
        logger.warning(
            "%s: hanya %d baris OHLCV (< %d). Fitur berwindow panjang (ma_dist_200, "
            "ma_dist_50) akan jatuh ke 0.0 dan TIDAK cocok dengan nilai saat training. "
            "Perpanjang periode fetch pemanggil.",
            tag, len(df), MIN_HISTORY_ROWS,
        )

    # ── Return & lag ────────────────────────────────────────────────────
    out['ret_1d'] = df['Close'].pct_change()
    for lag in range(1, 6):
        out[f'ret_1d_lag{lag}'] = out['ret_1d'].shift(lag)
    out['ret_2d'] = df['Close'].pct_change(2)
    out['ret_3d'] = df['Close'].pct_change(3)
    out['ret_5d'] = df['Close'].pct_change(5)
    out['ret_10d'] = df['Close'].pct_change(10)

    # ── Volatilitas ─────────────────────────────────────────────────────
    out['volatility_10d'] = out['ret_1d'].rolling(10).std()
    out['volatility_20d'] = out['ret_1d'].rolling(20).std()
    ret_mean = out['ret_1d'].rolling(20).mean()
    ret_std = out['ret_1d'].rolling(20).std().replace(0, np.nan)
    out['ret_1d_zscore'] = (out['ret_1d'] - ret_mean) / ret_std

    # ── Moving average ──────────────────────────────────────────────────
    ma5 = df['Close'].rolling(5).mean()
    ma20 = df['Close'].rolling(20).mean()
    ma50 = df['Close'].rolling(50).mean()
    ma200 = df['Close'].rolling(200).mean()
    out['ma_dist_5'] = df['Close'] / ma5 - 1
    out['ma_dist_20'] = df['Close'] / ma20 - 1
    out['ma_dist_50'] = df['Close'] / ma50 - 1
    out['ma_dist_200'] = df['Close'] / ma200 - 1
    out['is_bullish_trend'] = (ma20 > ma50).astype(float)

    # ── Indikator teknikal ──────────────────────────────────────────────
    rsi_series = _compute_rsi(df['Close'], 14)
    out['rsi'] = rsi_series
    # Di-shift 1 hari untuk menghindari lookahead pada sinyal hari yang sama.
    out['rsi_14_prev'] = rsi_series.shift(1)

    macd, macd_hist = _compute_macd(df['Close'])
    bb_upper, bb_lower = _compute_bb(df['Close'])
    stoch_k, stoch_d = _compute_stoch(df['High'], df['Low'], df['Close'])
    atr = _compute_atr(df['High'], df['Low'], df['Close'])
    out['macd'] = macd / df['Close']
    out['macd_hist'] = macd_hist / df['Close']
    out['bb_upper_dist'] = df['Close'] / bb_upper - 1
    out['bb_lower_dist'] = df['Close'] / bb_lower - 1
    out['stoch_k'] = stoch_k
    out['stoch_d'] = stoch_d
    out['atr'] = atr / df['Close']

    # ── Volume ──────────────────────────────────────────────────────────
    vol_ma20 = df['Volume'].rolling(20).mean()
    out['vol_ratio'] = df['Volume'] / vol_ma20
    out['volume_spike'] = df['Volume'] / vol_ma20
    out['volume_spike_prev'] = out['volume_spike'].shift(1)
    out['vol_trend_5d'] = df['Volume'].rolling(5).mean() / vol_ma20

    # ── Struktur candle ─────────────────────────────────────────────────
    out['range_pct'] = (df['High'] - df['Low']) / df['Close']
    out['gap_open'] = df['Open'] / df['Close'].shift(1) - 1
    candle_range = (df['High'] - df['Low']).replace(0, np.nan)
    out['close_to_high'] = (df['High'] - df['Close']) / df['Close']   # upper wick ratio
    out['close_to_low'] = (df['Close'] - df['Low']) / df['Close']     # lower wick
    out['body_ratio'] = (df['Close'] - df['Open']).abs() / candle_range.fillna(1e-8)
    out['gap_continuation'] = out['gap_open'] * out['ret_1d'].shift(1)
    out['day_of_week'] = pd.to_datetime(df.index).dayofweek.astype(float)

    # ── Candlestick pattern ─────────────────────────────────────────────
    body_size_h = (df['Close'] - df['Open']).abs()
    lower_wick_h = df[['Open', 'Close']].min(axis=1) - df['Low']
    upper_wick_h = df['High'] - df[['Open', 'Close']].max(axis=1)
    is_hammer_h = (lower_wick_h > 2 * body_size_h) & (upper_wick_h < 0.3 * body_size_h) & (df['Volume'] > vol_ma20)
    is_bull_eng_h = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] >= df['Open'].shift(1)) & (df['Open'] <= df['Close'].shift(1))
    is_bear_eng_h = (df['Close'] < df['Open']) & (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Open'] >= df['Close'].shift(1)) & (df['Close'] <= df['Open'].shift(1))
    out['is_bullish_pattern'] = (is_hammer_h | is_bull_eng_h).astype(float)
    out['is_bearish_pattern'] = is_bear_eng_h.astype(float)
    out['candlestick_winrate'] = np.where(
        is_bull_eng_h, 0.68, np.where(is_hammer_h, 0.64, np.where(is_bear_eng_h, 0.34, 0.50))
    )

    # ── Volume profile / orderbook proxy ────────────────────────────────
    roll20 = df.rolling(20, min_periods=10)
    price_min20 = roll20['Low'].min()
    price_max20 = roll20['High'].max()
    price_range20 = (price_max20 - price_min20).replace(0, np.nan)

    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    vwap20 = (tp * df['Volume']).rolling(20, min_periods=10).sum() / df['Volume'].rolling(20, min_periods=10).sum().replace(0, np.nan)
    out['vwap_deviation_20d'] = (df['Close'] / vwap20 - 1).fillna(0.0)

    upper = (df['High'] - tp).clip(lower=0)
    lower = (tp - df['Low']).clip(lower=0)
    out['ob_imbalance_proxy_20d'] = ((upper - lower) / df['Volume'].replace(0, np.nan)).rolling(20, min_periods=10).mean().fillna(0.0)
    out['signed_volume_20d'] = (out['ret_1d'] * df['Volume']).rolling(20, min_periods=10).sum().fillna(0.0)

    h5 = df['High'].rolling(5, min_periods=3).max()
    l5 = df['Low'].rolling(5, min_periods=3).min()
    out['range_concentration_20d'] = ((h5 - l5) / price_range20).fillna(0.0)

    close_pos = (df['Close'] - price_min20) / price_range20
    vol_sum20 = df['Volume'].rolling(20, min_periods=10).sum().replace(0, np.nan)
    for name, mask in (
        ('vol_profile_20d_upper', close_pos >= 0.66),
        ('vol_profile_20d_mid', (close_pos >= 0.33) & (close_pos < 0.66)),
        ('vol_profile_20d_lower', close_pos < 0.33),
    ):
        out[name] = ((df['Volume'] * mask.astype(int)).rolling(20, min_periods=10).sum() / vol_sum20).fillna(0.0)

    # ── Metadata Stockbit ───────────────────────────────────────────────
    # Dicocokkan case-insensitive lewat _pick_col(). Kalau kolomnya benar-benar
    # tidak ada (fallback yfinance), log warning — JANGAN diam-diam jatuh ke 0.0,
    # karena persis itu yang membuat bug NetForeign lolos berbulan-bulan.
    nf_col = _pick_col(df, 'NetForeign')
    if nf_col:
        out['day_foreign_net'] = df[nf_col] / 1e9
    else:
        logger.warning(
            f"{tag}: kolom NetForeign tidak ada — day_foreign_net, foreign_net_7d/1m, "
            f"foreign_flow_zscore akan konstan 0 (sumber data kemungkinan yfinance)"
        )
        out['day_foreign_net'] = 0.0
    out['foreign_net_7d'] = out['day_foreign_net'].rolling(7).sum().fillna(0.0)
    out['foreign_net_1m'] = out['day_foreign_net'].rolling(30).sum().fillna(0.0)

    fn7 = out['foreign_net_7d']
    fn_std = fn7.rolling(20).std().replace(0, np.nan)
    out['foreign_flow_zscore'] = ((fn7 - fn7.rolling(20).mean()) / fn_std).fillna(0.0)

    freq_col = _pick_col(df, 'Frequency')
    if freq_col:
        out['frequency_1d'] = df[freq_col]
    else:
        logger.warning(f"{tag}: kolom Frequency tidak ada — frequency_1d konstan 0")
        out['frequency_1d'] = 0.0

    avg_col = _pick_col(df, 'AveragePrice')
    if avg_col:
        out['close_vs_avg'] = (df['Close'] / df[avg_col].replace(0, np.nan) - 1).fillna(0.0)
    else:
        logger.warning(f"{tag}: kolom AveragePrice tidak ada — close_vs_avg konstan 0")
        out['close_vs_avg'] = 0.0

    # ── Konteks IHSG ────────────────────────────────────────────────────
    ihsg_cols = ['ihsg_ret_1d', 'ihsg_ret_5d', 'ihsg_rsi', 'ihsg_ma_dist_20',
                 'ihsg_volatility', 'ihsg_trend', 'ihsg_trend_3d']
    if ihsg is not None and not ihsg.empty and 'close' in ihsg:
        ic = pd.to_numeric(ihsg['close'], errors='coerce')
        ihsg_ma20 = ic.rolling(20).mean()
        ihsg_ma50 = ic.rolling(50).mean()
        ihsg_feats = pd.DataFrame({
            'ihsg_ret_1d': ic.pct_change(),
            'ihsg_ret_5d': ic.pct_change(5),
            # Sebelumnya prepare_training_data membaca 'ihsg_ret_3d' yang tidak pernah
            # dibuat, sehingga ihsg_trend_3d konstan 0 di training tapi bernilai nyata
            # di live inference.
            'ihsg_trend_3d': ic.pct_change(3),
            'ihsg_rsi': _compute_rsi(ic, 14),
            'ihsg_ma_dist_20': ic / ihsg_ma20 - 1,
            'ihsg_volatility': ic.pct_change().rolling(20).std(),
            'ihsg_trend': (ihsg_ma20 > ihsg_ma50).astype(float),
        }, index=ihsg.index)
        out = out.join(ihsg_feats, how='left')
        out['stock_vs_ihsg_1d'] = out['ret_1d'] - out['ihsg_ret_1d'].fillna(0)
    else:
        logger.warning(f"{tag}: history IHSG tidak tersedia — fitur konteks pasar konstan 0")
        for col in ihsg_cols:
            out[col] = 0.0
        out['stock_vs_ihsg_1d'] = 0.0

    for col in OHLCV_DERIVED_FEATURES:
        if col not in out.columns:
            out[col] = 0.0
    return out[OHLCV_DERIVED_FEATURES]


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

    # Targets: Binary classification — 1 for significant price increase, 0 otherwise
    # Thresholds tuned for >=50% buy precision target: 1D=0.6%, 3D=1.8%, 5D=2.5%, 7D=3.0%
    df['target_1d'] = (df['Close'].shift(-1) > df['Close'] * 1.006).astype(int)
    df['target_3d'] = (df['Close'].shift(-3) > df['Close'] * 1.018).astype(int)
    df['target_5d'] = (df['Close'].shift(-5) > df['Close'] * 1.025).astype(int)
    df['target_7d'] = (df['Close'].shift(-7) > df['Close'] * 1.030).astype(int)

    # Seluruh fitur turunan data pasar dihitung oleh SATU fungsi yang dipakai
    # bersama dengan extract_features() — lihat compute_ohlcv_features().
    # Sebelumnya blok ini diduplikasi di jalur live inference dan 13 fitur
    # diam-diam melenceng definisinya.
    market = compute_ohlcv_features(df, ihsg=_fetch_ihsg_history(), ticker=ticker)
    df = df.join(market, how="left")

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
                        "buy_value": float(r.buy_value or 0)
                    } for r in accum_rows])
                    
                    df_daily = df_accum.groupby("date").agg({
                        "buy_lot": "sum",
                        "buy_value": "sum"
                    }).sort_index()
                    
                    # Compute rolling sums on the daily grouped accumulation
                    roll7_val = df_daily["buy_value"].rolling(7).sum()
                    roll7_lot = df_daily["buy_lot"].rolling(7).sum()
                    df_daily["avg_7d"] = roll7_val / (roll7_lot * 100)
                    
                    roll30_val = df_daily["buy_value"].rolling(30).sum()
                    roll30_lot = df_daily["buy_lot"].rolling(30).sum()
                    df_daily["avg_1m"] = roll30_val / (roll30_lot * 100)
                    
                    db_accum = df_daily[["avg_7d", "avg_1m"]]
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

    # ── Fitur sektor DIHAPUS (look-ahead) ─────────────────────────────────
    # Blok sebelumnya di sini menghitung dominant_sector_ret_1d/5d,
    # stock_vs_sector_1d/5d, dan sector_strength_vs_ihsg sebagai SKALAR dari
    # tanggal TERAKHIR, lalu menyiarkannya ke seluruh baris (`df[col] = val`).
    # Artinya baris training tahun 2019 menerima nilai sektor tahun 2026 —
    # look-ahead penuh. Selama ini tidak berdampak hanya karena fitur-fitur itu
    # tidak ada di FEATURE_COLUMNS sehingga terbuang saat `return df[FEATURE_COLUMNS]`,
    # jadi ia landmine yang menunggu seseorang menambahkannya ke daftar fitur.
    #
    # Bonus: implementasinya juga sudah mati tanpa disadari —
    # `index.get_loc(td, method="nearest")` memakai argumen yang dihapus di
    # pandas 2.x, sehingga selalu masuk `except` dan mengembalikan 0.0.
    #
    # Kalau fitur sektor mau dihidupkan lagi, hitung per-baris secara vectorized
    # di compute_ohlcv_features() (butuh universe OHLCV sebagai input), JANGAN
    # sebagai skalar yang disiarkan.
    if universe_ohlcv:
        logger.debug(
            "universe_ohlcv diberikan tapi fitur sektor sudah dihapus (look-ahead); "
            "argumen ini kini tidak dipakai."
        )

    # Fill default baseline values for missing DB features
    df["bandarm_score"] = df.get("bandarm_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["technical_score"] = df.get("technical_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["macro_score"] = df.get("macro_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    
    # NEW PARAMETERS FOR BRAINSTORM
    # Catatan: ketiganya konstan 5.0 di training. news_score & commodity_score sudah
    # dikeluarkan dari ML_TRAIN_FEATURES karena konstan di training tapi bervariasi
    # di live inference — kondisi yang strictly lebih buruk daripada tidak ada fitur.
    df["fundamental_score"] = df.get("fundamental_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["news_score"] = df.get("news_score", pd.Series(5.0, index=df.index)).fillna(5.0)
    df["commodity_score"] = df.get("commodity_score", pd.Series(5.0, index=df.index)).fillna(5.0)

    df["dist_avg_7d"] = df.get("dist_avg_7d", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["dist_avg_1m"] = df.get("dist_avg_1m", pd.Series(0.0, index=df.index)).fillna(0.0)
    df["is_retail_accum"] = df.get("is_retail_accum", pd.Series(0.0, index=df.index)).fillna(0.0)

    # foreign_net_7d/1m, foreign_flow_zscore, dan ihsg_trend_3d TIDAK dihitung di sini
    # lagi — semuanya berasal dari compute_ohlcv_features(). Baris lama yang mengisi
    # ihsg_trend_3d dari kolom 'ihsg_ret_3d' (yang tidak pernah dibuat) justru akan
    # menimpa nilai yang benar dengan 0.
    df["bandar_accum_ratio"] = _bandar_accum_ratio(
        df["foreign_net_1m"].fillna(0.0), df["dist_avg_1m"].fillna(0.0)
    )

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
