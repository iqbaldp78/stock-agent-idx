"""
ML Predictor Engine (LightGBM)
Training dan inference untuk prediksi return Day-1 (T+1).
"""
import lightgbm as lgb
import pandas as pd
import numpy as np
import logging
import joblib
import os
from data.ml_features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

class Day1Predictor:
    def __init__(self, model_path: str = "models/checkpoints/lgbm_day1.pkl"):
        self.model_path = model_path
        self.model = None
        self.feature_cols = FEATURE_COLUMNS

        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded existing model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    def train_incremental(self, X: pd.DataFrame, y):
        """
        Train or update model with new data.
        Currently uses simple LGBM Regressor.
        """
        if len(X) < 10:
            logger.warning("Not enough data to train.")
            return

        # If y is a DataFrame from new ml_features, take the first column (target_1d)
        if isinstance(y, pd.DataFrame):
            if 'target_1d' in y.columns:
                y = y['target_1d']
            else:
                y = y.iloc[:, 0]

        # Drop NaNs
        valid_idx = ~y.isna()
        if not valid_idx.any():
            return

        X_aligned = self._align_feature_frame(X)[valid_idx]
        y_valid = y[valid_idx]

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

        dtrain = lgb.Dataset(X_aligned, label=y_valid)
        self.model = lgb.train(params, dtrain, num_boost_round=300)

        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def predict(self, feature_row: pd.DataFrame) -> float:
        """
        Predict return for tomorrow.
        """
        if self.model is None:
            # Fallback: simple weighted score if no ML model yet
            logger.warning("No ML model found, using rule-based fallback prediction.")
            return self._rule_based_prediction(feature_row)

        try:
            model_cols = self.model.feature_name() if hasattr(self.model, "feature_name") else []
            if model_cols:
                aligned = feature_row.copy()
                for col in model_cols:
                    if col not in aligned.columns:
                        aligned[col] = 0.0
                pred = self.model.predict(aligned[model_cols])
            else:
                pred = self.model.predict(self._align_feature_frame(feature_row))
        except Exception as e:
            logger.warning("Model predict failed (%s), fallback to rule-based.", e)
            return self._rule_based_prediction(feature_row)
        return float(pred[0])

    def _align_feature_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.copy()
        for col in self.feature_cols:
            if col not in aligned.columns:
                aligned[col] = 0.0
        return aligned[self.feature_cols].fillna(0.0)

    def _rule_based_prediction(self, feature_row: pd.DataFrame) -> float:
        """
        Emergency fallback prediction.
        """
        score = (
            feature_row['bandarm_score'].iloc[0] * 0.4 +
            feature_row['technical_score'].iloc[0] * 0.3 +
            (1.0 if feature_row['is_bullish_trend'].iloc[0] > 0.5 else -0.5) * 0.2 +
            feature_row['macro_score'].iloc[0] * 0.1
        )
        # Map 1-10 score to roughly -2% to +2% return
        return (score - 5.5) / 100.0

    def get_signal(self, pred_return: float) -> str:
        """
        Convert predicted return to signal string.
        """
        if pred_return >= 0.01: return "STRONG BUY"
        if pred_return >= 0.003: return "BUY"
        if pred_return <= -0.005: return "AVOID"
        return "HOLD"
