"""
ML Predictor Engine (LightGBM)
Training dan inference untuk prediksi return T+1, T+3, T+5, T+7.
Menggunakan 4 model independen untuk mempelajari pola pergerakan harga di masing-masing horizon waktu.
"""
import lightgbm as lgb
import pandas as pd
import numpy as np
import logging
import joblib
import os
from data.ml_features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

class MultiDayPredictor:
    def __init__(self, checkpoints_dir: str = "models/checkpoints"):
        self.checkpoints_dir = checkpoints_dir
        self.feature_cols = FEATURE_COLUMNS
        self.horizons = ['1d', '3d', '5d', '7d']
        self.models = {h: None for h in self.horizons}

        self._load_models()

    def _get_model_path(self, horizon: str) -> str:
        return os.path.join(self.checkpoints_dir, f"lgbm_{horizon}.pkl")

    def _load_models(self):
        for h in self.horizons:
            path = self._get_model_path(h)
            if os.path.exists(path):
                try:
                    self.models[h] = joblib.load(path)
                    logger.info(f"Loaded {h} model from {path}")
                except Exception as e:
                    logger.warning(f"Failed to load {h} model: {e}")

    def train_incremental(self, X: pd.DataFrame, Y_targets: pd.DataFrame):
        """
        Train 4 independent models for 1d, 3d, 5d, and 7d horizons.
        Y_targets should have columns: target_1d, target_3d, target_5d, target_7d
        """
        if len(X) < 10:
            logger.warning("Not enough data to train.")
            return

        X_aligned = self._align_feature_frame(X)

        # Base parameters - can be tuned individually per horizon later
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'learning_rate': 0.05,
            'num_leaves': 64,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5
        }

        os.makedirs(self.checkpoints_dir, exist_ok=True)

        for h in self.horizons:
            col_name = f'target_{h}'
            if col_name not in Y_targets.columns:
                logger.warning(f"Target {col_name} not found in Y_targets. Skipping training for {h}.")
                continue

            y = Y_targets[col_name]
            # Drop NaNs if any specific to this horizon
            valid_idx = ~y.isna()
            if not valid_idx.any():
                continue

            X_valid = X_aligned[valid_idx]
            y_valid = y[valid_idx]

            logger.info(f"Training model for horizon: {h} on {len(X_valid)} samples")
            dtrain = lgb.Dataset(X_valid, label=y_valid)

            # For longer horizons, maybe use fewer boosting rounds to prevent overfitting
            # but for now we use 300 for all
            self.models[h] = lgb.train(params, dtrain, num_boost_round=300)

            # Save model
            model_path = self._get_model_path(h)
            joblib.dump(self.models[h], model_path)
            logger.info(f"Model {h} saved to {model_path}")

    def predict(self, feature_row: pd.DataFrame) -> dict:
        """
        Predict return for 1d, 3d, 5d, 7d.
        Returns a dictionary with raw percentage predictions.
        """
        predictions = {}

        for h in self.horizons:
            model = self.models[h]
            if model is None:
                # Fallback rule-based if ML not available
                predictions[h] = self._rule_based_prediction(feature_row, h)
                continue

            try:
                model_cols = model.feature_name() if hasattr(model, "feature_name") else []
                if model_cols:
                    aligned = feature_row.copy()
                    for col in model_cols:
                        if col not in aligned.columns:
                            aligned[col] = 0.0
                    pred = model.predict(aligned[model_cols])
                else:
                    pred = model.predict(self._align_feature_frame(feature_row))
                predictions[h] = float(pred[0])
            except Exception as e:
                logger.warning("Model predict failed for %s (%s), fallback to rule-based.", h, e)
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
        Uses original linear logic logic.
        """
        score = (
            feature_row['bandarm_score'].iloc[0] * 0.4 +
            feature_row['technical_score'].iloc[0] * 0.3 +
            (1.0 if feature_row['is_bullish_trend'].iloc[0] > 0.5 else -0.5) * 0.2 +
            feature_row['macro_score'].iloc[0] * 0.1
        )
        # Map 1-10 score to roughly -2% to +2% return base
        base_pct = (score - 5.5) / 100.0

        factors = {'1d': 1.0, '3d': 3.0, '5d': 5.0, '7d': 7.0}
        return base_pct * factors.get(horizon, 1.0)

    def get_signal(self, pred_return_1d: float) -> str:
        """
        Convert predicted 1d return to signal string.
        (Retained for backward compatibility)
        """
        if pred_return_1d >= 0.01: return "STRONG BUY"
        if pred_return_1d >= 0.003: return "BUY"
        if pred_return_1d <= -0.005: return "AVOID"
        return "HOLD"
