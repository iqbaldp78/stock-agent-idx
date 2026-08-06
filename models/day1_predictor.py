"""
ML Predictor Engine (LightGBM)
Training dan inference untuk prediksi return Day-1 (T+1).
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
from data.ml_features import ML_TRAIN_FEATURES
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

logger = logging.getLogger(__name__)

class Day1Predictor:
    def __init__(self, model_path: str = "models/checkpoints/lgbm_day1.pkl", target_col: str = "target_1d"):
        self.model_path = model_path
        self.target_col = target_col
        self.model = None
        self.feature_cols = ML_TRAIN_FEATURES

        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded existing model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    def train_incremental(self, X: pd.DataFrame, y):
        """
        Train or update model with new data.
        Uses regression target magnitude with time-decay sample weighting.
        """
        if len(X) < 10:
            logger.warning("Not enough data to train.")
            return

        # If y is a DataFrame, take the specified target column
        if isinstance(y, pd.DataFrame):
            if self.target_col in y.columns:
                y = y[self.target_col]
            else:
                y = y.iloc[:, 0]

        # Drop NaNs
        valid_idx = ~y.isna()
        if not valid_idx.any():
            return

        X_aligned = self._align_feature_frame(X)[valid_idx]
        y_valid = y[valid_idx].astype(float)

        logger.info(
            f"Training regression on {len(X_aligned)} samples "
            f"target_col={self.target_col}"
        )

        # ── Time-decay sample weights ─────────────────────────────────────
        # Exponential decay: recent data weighted ~3x more than oldest data
        n_samples = len(X_aligned)
        decay_factor = 3.0  # newest/oldest weight ratio
        weights = np.exp(np.linspace(0, np.log(decay_factor), n_samples))
        weights = weights / weights.mean()  # normalize to mean=1

        # ── Lightweight ensemble: 3 LightGBM with different seeds ────────
        base_estimator = lgb.LGBMRegressor(verbosity=-1, bagging_freq=1)

        param_dist = {
            'objective': ['regression'],
            'metric': ['rmse'],
            'learning_rate': [0.01, 0.03, 0.05, 0.1],
            'num_leaves': [7, 15, 31, 63],
            'min_child_samples': [20, 50, 100, 200],
            'bagging_fraction': [0.5, 0.6, 0.7, 0.8],
            'feature_fraction': [0.5, 0.6, 0.7, 0.8],
            'n_estimators': [100, 200, 300, 500],
            'reg_alpha': [0.0, 0.1, 0.5, 1.0],       # L1 regularization
            'reg_lambda': [0.0, 0.1, 0.5, 1.0],      # L2 regularization
            'min_gain_to_split': [0.0, 0.01, 0.05],  # prune weak splits
        }

        tscv = TimeSeriesSplit(n_splits=3)

        best_models = []
        best_scores = []
        for seed in (7, 13, 42):
            estimator = lgb.LGBMRegressor(verbosity=-1, bagging_freq=1, random_state=seed)
            random_search = RandomizedSearchCV(
                estimator, param_distributions=param_dist,
                n_iter=20, cv=tscv,
                scoring='neg_mean_squared_error',
                random_state=seed, n_jobs=1
            )
            random_search.fit(X_aligned, y_valid, sample_weight=weights)
            best_models.append(random_search.best_estimator_)
            best_scores.append(float((-random_search.best_score_) ** 0.5))

        # Pick best seed by CV RMSE; still keep ensemble weights later
        best_idx = int(np.argmin(best_scores))
        self.model = best_models[best_idx]

        logger.info("Ensemble seeds RMSE: " + ", ".join(f"{s:.4f}" for s in best_scores))
        logger.info(f"Selected seed best RMSE: {best_scores[best_idx]:.4f}")

        # Save ensemble sidecar for inference averaging
        ensemble_path = self.model_path + ".ensemble.json"
        try:
            import json as _json
            payload = {
                "seeds": [7, 13, 42],
                "best_seed": int(best_idx),
                "feature_cols": list(self.feature_cols),
            }
            with open(ensemble_path, "w") as f:
                _json.dump(payload, f)
        except Exception as e:
            logger.warning(f"Failed to save ensemble metadata: {e}")

        logger.info(f"Best RMSE (CV): {best_scores[best_idx]:.4f}")

        # Save primary model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def predict(self, feature_row: pd.DataFrame) -> float:
        """
        Predict return for tomorrow using ML + Agent Score Ensemble.
        Returns predicted % return as float.
        """
        ml_pred = 0.0
        if self.model is not None:
            try:
                model_cols = self._model_feature_names()
                aligned = feature_row.copy()
                for col in model_cols:
                    if col not in aligned.columns:
                        aligned[col] = 0.0
                pred = self.model.predict(aligned[model_cols])
                ml_pred = float(pred[0])
            except Exception as e:
                logger.warning("Model predict failed (%s), fallback to 0.0.", e)
        
        return self._ensemble_prediction(feature_row, ml_pred)

    def _model_feature_names(self) -> list:
        """
        Kolom yang BENAR-BENAR dipakai model saat dilatih.

        Penting: sklearn API LightGBM mengekspos `feature_name_` (atribut), bukan
        `feature_name()` (method). Kode lama memakai
        `hasattr(model, "feature_name")` yang SELALU False, sehingga selalu jatuh ke
        ML_TRAIN_FEATURES. Akibatnya begitu ML_TRAIN_FEATURES berubah, model lama
        di disk langsung error karena jumlah fitur tidak cocok.

        Memakai kolom milik model membuat artefak lama tetap bisa dipakai, dan
        ketidakcocokan versi terlihat sebagai warning, bukan crash.
        """
        names = getattr(self.model, "feature_name_", None)
        if names is not None and len(names):
            names = list(names)
            if names != list(self.feature_cols):
                logger.warning(
                    "Model %s dilatih dengan %d fitur, sementara ML_TRAIN_FEATURES "
                    "sekarang %d. Memakai kolom milik model; latih ulang agar selaras.",
                    self.model_path, len(names), len(self.feature_cols),
                )
            return names
        return list(self.feature_cols)

    def _align_feature_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.copy()
        for col in self.feature_cols:
            if col not in aligned.columns:
                aligned[col] = 0.0
        return aligned[self.feature_cols].fillna(0.0)

    def _ensemble_prediction(self, feature_row: pd.DataFrame, ml_pred: float) -> float:
        """
        Combine ML prediction with agent Bandarmologi and Technical scores.
        """
        bandarm_score = feature_row.get('bandarm_score', pd.Series([5.0])).iloc[0]
        tech_score = feature_row.get('technical_score', pd.Series([5.0])).iloc[0]
        
        # 1 pt above neutral (5.0) contributes +0.5% return
        bandarm_effect = (bandarm_score - 5.0) * 0.005
        tech_effect = (tech_score - 5.0) * 0.002
        
        final_pred = ml_pred * 0.7 + bandarm_effect + tech_effect
        return final_pred

    def get_signal(self, pred_return: float) -> str:
        """
        Convert predicted return to signal string.
        """
        if pred_return >= 0.02: return "STRONG BUY"
        if pred_return >= 0.005: return "BUY"
        if pred_return <= -0.01: return "AVOID"
        return "HOLD"
