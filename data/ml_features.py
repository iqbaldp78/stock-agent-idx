"""
Feature Engineering for ML Prediction
Mengonversi output agent (JSON) dan data raw (OHLCV) menjadi fitur numerik.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "bandarm_score",
    "dist_avg_7d",
    "dist_avg_1m",
    "foreign_net_7d",
    "foreign_net_1m",
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
]

# Kolom yang benar-benar digunakan untuk melatih ML (hanya yang bisa dihitung secara historis)
ML_TRAIN_FEATURES = [
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
]


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


def _proximity(current_price: float, level: float) -> float:
    if current_price <= 0 or level <= 0:
        return 0.0
    return (current_price - level) / current_price

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

    bandar_features = {
        "bandarm_score": bandarm.get("score", 5.0),
        "dist_avg_7d": _parse_pct(price_analysis.get("distance_from_7d")),
        "dist_avg_1m": _parse_pct(price_analysis.get("distance_from_1m")),
        "foreign_net_7d": _parse_number(bandarm.get("window_7d", {}).get("foreign_net_7d"), 0.0) / 1e9, # In Billions
        "foreign_net_1m": _parse_number(bandarm.get("window_1m", {}).get("foreign_net_1m"), 0.0) / 1e9,
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
            "macd": float(macd.iloc[-1]) if len(macd.dropna()) > 0 else 0.0,
            "macd_hist": float(macd_hist.iloc[-1]) if len(macd_hist.dropna()) > 0 else 0.0,
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

def prepare_training_data(ohlcv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate historical features and targets from OHLCV for training.
    Returns (features_df, targets_df) where targets_df contains columns for 1d, 3d, 5d, and 7d horizons.
    """
    df = ohlcv.copy()

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

    df['macd'] = macd
    df['macd_hist'] = macd_hist
    df['bb_upper_dist'] = df['Close'] / bb_upper - 1
    df['bb_lower_dist'] = df['Close'] / bb_lower - 1
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    df['atr'] = atr / df['Close']

    # Drop rows with NaN (from rolling/shifting)
    df = df.dropna()

    # Keep the existing model schema: non-OHLCV features are placeholders for historical training.
    # Note: ML Model will only use ML_TRAIN_FEATURES
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    targets = df[['target_1d', 'target_3d', 'target_5d', 'target_7d']]
    # We return the full FEATURE_COLUMNS for backward compatibility, but models/day1_predictor 
    # will only select ML_TRAIN_FEATURES.
    return df[FEATURE_COLUMNS], targets
