"""
ML Predictor Engine (LightGBM)
Training dan inference untuk prediksi return T+1, T+3, T+5, T+7.
Menggunakan 4 model independen untuk mempelajari pola pergerakan harga di masing-masing horizon waktu.
Ditingkatkan dengan:
- Purged TimeSeriesSplit CV (mencegah data leakage)
- Feature Selection 2-stage (eliminasi 0-importance noise features)
- Hyperparameter Tuning (RandomizedSearchCV)
- Class Imbalance & Scale Pos Weight Tuning
- Probability Calibration (CalibratedClassifierCV)
- Per-ticker per-horizon Optimal F1 Threshold Selection
"""
import warnings
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass

import lightgbm as lgb
import pandas as pd
import numpy as np
import logging
import joblib
import os
import json
from sklearn.model_selection import RandomizedSearchCV
from sklearn.calibration import CalibratedClassifierCV
from data.ml_features import ML_TRAIN_FEATURES

logger = logging.getLogger(__name__)


class PurgedTimeSeriesSplit:
    """
    Time-Series Split with Purging Gap to prevent label overlap leakage.
    """
    def __init__(self, n_splits=3, gap=7):
        self.n_splits = n_splits
        self.gap = gap

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits

    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        fold_size = n_samples // (self.n_splits + 1)
        for i in range(self.n_splits):
            train_end = fold_size * (i + 1)
            val_start = train_end + self.gap
            val_end = min(val_start + fold_size, n_samples)
            if val_start < n_samples and (val_end - val_start) > 0:
                train_indices = np.arange(0, train_end)
                val_indices = np.arange(val_start, val_end)
                yield train_indices, val_indices


def pick_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray, min_precision: float = 0.50, default: float = 0.50) -> float:
    """
    Pick threshold in [0.35, 0.70] that maximizes combined Accuracy and F1 score with min_precision >= 50%.
    """
    if len(y_true) == 0 or len(y_prob) == 0:
        return default

    candidates = []
    for thr in np.linspace(0.35, 0.70, 36):
        pred_buy = (y_prob >= thr).astype(int)
        acc = np.mean(pred_buy == y_true)
        tp = np.sum((pred_buy == 1) & (y_true == 1))
        fp = np.sum((pred_buy == 1) & (y_true == 0))
        fn = np.sum((pred_buy == 0) & (y_true == 1))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        combined_score = 0.3 * acc + 0.7 * f1
        if prec >= min_precision:
            candidates.append((combined_score, acc, prec, rec, thr))

    if candidates:
        candidates.sort(reverse=True)
        return _warn_if_pinned(float(candidates[0][4]))

    # Tidak ada threshold yang memenuhi min_precision — longgarkan syaratnya.
    # Ini sendiri sudah pertanda model lemah, jadi dicatat.
    logger.warning(
        "Tidak ada threshold dengan precision >= %.2f; jatuh ke pemilihan tanpa "
        "batas precision. Model kemungkinan tidak punya daya separasi.", min_precision,
    )
    best_score = -1.0
    best_thr = default
    for thr in np.linspace(0.35, 0.70, 36):
        pred_buy = (y_prob >= thr).astype(int)
        acc = np.mean(pred_buy == y_true)
        tp = np.sum((pred_buy == 1) & (y_true == 1))
        fp = np.sum((pred_buy == 1) & (y_true == 0))
        fn = np.sum((pred_buy == 0) & (y_true == 1))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        combined_score = 0.3 * acc + 0.7 * f1
        if combined_score > best_score:
            best_score = combined_score
            best_thr = float(thr)

    return _warn_if_pinned(float(best_thr), "fallback tanpa batas precision")


class MultiDayPredictor:
    def __init__(self, ticker: str = "GLOBAL", checkpoints_dir: str = "models/checkpoints"):
        self.ticker = ticker.upper()
        self.checkpoints_dir = checkpoints_dir
        self.feature_cols = ML_TRAIN_FEATURES
        self.horizons = ['1d', '3d', '5d', '7d']
        self.horizon_gaps = {'1d': 1, '3d': 3, '5d': 5, '7d': 7}
        self.models = {h: None for h in self.horizons}
        self.thresholds = {h: 0.50 for h in self.horizons}
        self.selected_features = {h: ML_TRAIN_FEATURES for h in self.horizons}

        self._load_models()

    def _get_model_path(self, horizon: str) -> str:
        return os.path.join(self.checkpoints_dir, f"lgbm_{self.ticker}_{horizon}.pkl")

    def _get_threshold_path(self, horizon: str) -> str:
        return os.path.join(self.checkpoints_dir, f"lgbm_{self.ticker}_{horizon}_threshold.json")

    def _get_features_path(self, horizon: str) -> str:
        return os.path.join(self.checkpoints_dir, f"lgbm_{self.ticker}_{horizon}_features.json")

    def _load_models(self):
        # Kegagalan load HARUS terlihat di log level produksi. Versi sebelumnya
        # memakai logger.debug dan tidak melaporkan apa pun ketika file model
        # sekadar tidak ada — sehingga seluruh inferensi jatuh ke
        # _rule_based_prediction() tanpa jejak apa pun selama berbulan-bulan.
        missing = []
        for h in self.horizons:
            path = self._get_model_path(h)
            if os.path.exists(path):
                try:
                    self.models[h] = joblib.load(path)
                except Exception as e:
                    logger.warning(
                        "Model %s [%s] ada di %s tapi gagal di-load: %s. "
                        "Prediksi horizon ini akan memakai fallback rule-based.",
                        self.ticker, h, path, e,
                    )
            else:
                missing.append(h)

            thr_path = self._get_threshold_path(h)
            if os.path.exists(thr_path):
                try:
                    with open(thr_path, "r") as f:
                        data = json.load(f)
                        self.thresholds[h] = float(data.get("buy_threshold", 0.50))
                except Exception as e:
                    logger.debug(f"Failed to load threshold for {h}: {e}")

            feat_path = self._get_features_path(h)
            if os.path.exists(feat_path):
                try:
                    with open(feat_path, "r") as f:
                        data = json.load(f)
                        feats = data.get("selected_features", [])
                        if feats:
                            self.selected_features[h] = feats
                except Exception as e:
                    logger.debug(f"Failed to load features for {h}: {e}")

        if missing:
            logger.warning(
                "%s: model tidak ditemukan untuk horizon %s di %s. Prediksi horizon "
                "tersebut memakai _rule_based_prediction() — BUKAN ML. Jalankan "
                "`make train-ml-multiday` untuk membuatnya.",
                self.ticker, "/".join(missing), self.checkpoints_dir,
            )

    def has_model(self, horizon: str = None) -> bool:
        """
        Apakah prediksi berasal dari model terlatih, bukan fallback rule-based?

        Dipakai pemanggil yang perlu membedakan keduanya — hasil predict() sendiri
        berupa angka probabilitas yang tampak wajar untuk kedua kasus, sehingga
        tidak bisa dibedakan dari nilainya saja.
        """
        if horizon is not None:
            return self.models.get(horizon) is not None
        return any(self.models.get(h) is not None for h in self.horizons)

    def train_incremental(
        self,
        X_train: pd.DataFrame,
        Y_targets_train: pd.DataFrame,
        X_val: pd.DataFrame = None,
        Y_targets_val: pd.DataFrame = None
    ):
        """
        Train 4 independent models for 1d, 3d, 5d, and 7d horizons.
        Includes Feature Selection, Hyperparameter Tuning, Purged CV, Calibration, and Optimal Threshold.
        """
        if len(X_train) < 10:
            logger.warning(f"Not enough data to train {self.ticker}.")
            return

        X_train_aligned = self._align_feature_frame(X_train)
        X_val_aligned = self._align_feature_frame(X_val) if X_val is not None else None

        os.makedirs(self.checkpoints_dir, exist_ok=True)

        for h in self.horizons:
            col_name = f'target_{h}'
            if col_name not in Y_targets_train.columns:
                continue

            y_train = Y_targets_train[col_name]
            valid_idx = ~y_train.isna()
            if not valid_idx.any():
                continue

            X_tr = X_train_aligned[valid_idx].copy()
            y_tr = y_train[valid_idx].astype(int)

            # Check positive class availability
            if y_tr.nunique() < 2:
                logger.warning(f"Only one class present in target_{h} for {self.ticker}. Skipping.")
                continue

            # Time-decay sample weights
            n_samples = len(X_tr)
            decay_factor = 3.0
            weights = np.exp(np.linspace(0, np.log(decay_factor), n_samples))
            weights = weights / weights.mean()

            # ── 1. Feature Selection (Stage 1: Initial Discovery) ─────────
            base_discovery = lgb.LGBMClassifier(
                verbosity=-1,
                random_state=42,
                n_estimators=50,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8
            )
            base_discovery.fit(X_tr, y_tr, sample_weight=weights)
            importances = base_discovery.feature_importances_
            
            # Select features with non-zero importance
            selected_cols = [col for col, imp in zip(self.feature_cols, importances) if imp > 0]
            if len(selected_cols) < 5:
                # Fallback if too few features selected
                top_indices = np.argsort(importances)[::-1][:15]
                selected_cols = [self.feature_cols[i] for i in top_indices if i < len(self.feature_cols)]

            self.selected_features[h] = selected_cols
            X_tr_sel = X_tr[selected_cols]

            # ── 2. Purged Cross-Validation & Hyperparameter Tuning ────────
            n_splits = 3 if len(X_tr) < 100 else 4
            gap = self.horizon_gaps.get(h, 7)
            purged_cv = PurgedTimeSeriesSplit(n_splits=n_splits, gap=gap)

            param_dist = {
                'learning_rate': [0.01, 0.02, 0.03, 0.05],
                'num_leaves': [7, 15, 31],
                'min_child_samples': [20, 50, 100],
                'subsample': [0.6, 0.7, 0.8],
                'colsample_bytree': [0.5, 0.6, 0.7],
                'reg_alpha': [0.1, 0.5, 1.0, 2.0],
                'reg_lambda': [0.1, 0.5, 1.0, 2.0],
                'scale_pos_weight': [1.0, 1.5, 2.0],
                'n_estimators': [100, 150, 200, 300],
                'max_depth': [3, 5, 7],
            }

            from sklearn.metrics import make_scorer, f1_score
            f1_scorer = make_scorer(f1_score, zero_division=0)

            estimator = lgb.LGBMClassifier(verbosity=-1, random_state=42)
            search = RandomizedSearchCV(
                estimator=estimator,
                param_distributions=param_dist,
                n_iter=20,
                cv=purged_cv,
                scoring=f1_scorer,
                error_score=0.0,
                random_state=42,
                n_jobs=-1
            )

            search.fit(X_tr_sel, y_tr, sample_weight=weights)
            best_model = search.best_estimator_

            # ── 3. Probability Calibration & Optimal Threshold Selection ─
            final_model = best_model
            opt_thr = 0.50

            if X_val_aligned is not None and col_name in Y_targets_val.columns:
                y_val_raw = Y_targets_val[col_name]
                val_idx = ~y_val_raw.isna()
                if val_idx.any():
                    X_v_sel = X_val_aligned[val_idx][selected_cols]
                    y_v = y_val_raw[val_idx].astype(int)

                    if len(y_v) >= 10 and y_v.nunique() > 1:
                        # Calibrate model using validation fold
                        try:
                            calibrator = CalibratedClassifierCV(best_model, cv='prefit', method='sigmoid')
                            calibrator.fit(X_v_sel, y_v)
                            final_model = calibrator
                        except Exception as e:
                            logger.debug(f"Calibration failed for {h}: {e}")

                    # Predict probabilities on validation set for threshold tuning
                    val_probs = final_model.predict_proba(X_v_sel)[:, 1]
                    opt_thr = pick_optimal_threshold(y_v.values, val_probs)
            else:
                # OOF predictions on train set for threshold tuning fallback
                try:
                    train_probs = best_model.predict_proba(X_tr_sel)[:, 1]
                    opt_thr = pick_optimal_threshold(y_tr.values, train_probs)
                except Exception:
                    opt_thr = 0.50

            self.models[h] = final_model
            self.thresholds[h] = opt_thr

            # ── 4. Save Model & Sidecar Metadata ─────────────────────────
            model_path = self._get_model_path(h)
            joblib.dump(final_model, model_path)

            thr_path = self._get_threshold_path(h)
            with open(thr_path, "w") as f:
                json.dump({"buy_threshold": float(opt_thr)}, f)

            feat_path = self._get_features_path(h)
            with open(feat_path, "w") as f:
                json.dump({"selected_features": selected_cols}, f)

            logger.info(
                f"Trained {self.ticker} [{h}]: {len(selected_cols)} features, "
                f"best_params={search.best_params_}, opt_thr={opt_thr:.3f}"
            )

    def predict(self, feature_row: pd.DataFrame) -> dict:
        """
        Predict probability of positive price movement for 1d, 3d, 5d, 7d horizons.
        Returns dictionary with predicted probabilities.
        """
        predictions = {}

        for h in self.horizons:
            model = self.models[h]
            if model is None:
                predictions[h] = self._rule_based_prediction(feature_row, h)
                continue

            try:
                selected_cols = self.selected_features.get(h, self.feature_cols)
                aligned = feature_row.copy()
                for col in selected_cols:
                    if col not in aligned.columns:
                        aligned[col] = 0.0

                input_data = aligned[selected_cols].fillna(0.0)

                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(input_data)
                    predictions[h] = float(probs[0, 1])
                else:
                    preds = model.predict(input_data)
                    predictions[h] = float(preds[0])
            except Exception as e:
                logger.warning(f"Model predict failed for {h} ({e}), fallback to rule-based.")
                predictions[h] = self._rule_based_prediction(feature_row, h)

        return predictions

    def _align_feature_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.copy()
        for col in self.feature_cols:
            if col not in aligned.columns:
                aligned[col] = 0.0
        return aligned[self.feature_cols].fillna(0.0)

    def _rule_based_prediction(self, feature_row: pd.DataFrame, horizon: str) -> float:
        """
        Emergency fallback prediction if ML model is missing.
        """
        bandarm = feature_row.get('bandarm_score', pd.Series([5.0])).iloc[0]
        tech = feature_row.get('technical_score', pd.Series([5.0])).iloc[0]
        is_bull = 1.0 if feature_row.get('is_bullish_trend', pd.Series([0.0])).iloc[0] > 0.5 else -0.5
        macro = feature_row.get('macro_score', pd.Series([5.0])).iloc[0]

        score = bandarm * 0.4 + tech * 0.3 + is_bull * 0.2 + macro * 0.1
        prob = 0.50 + (score - 5.5) * 0.02
        return float(max(0.0, min(1.0, prob)))

    def get_signal(self, pred_prob_1d: float, horizon: str = '1d') -> str:
        """
        Convert predicted probability to signal string using per-ticker optimal threshold.
        """
        thr = self.thresholds.get(horizon, 0.50)

        if pred_prob_1d >= thr * 1.10:
            return "STRONG BUY"
        if pred_prob_1d >= thr:
            return "BUY"
        if pred_prob_1d <= max(0.20, thr * 0.80):
            return "AVOID"
        return "HOLD"
