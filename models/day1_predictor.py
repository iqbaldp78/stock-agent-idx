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
from data.ml_features import ML_TRAIN_FEATURES
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

logger = logging.getLogger(__name__)

class Day1Predictor:
    def __init__(self, model_path: str = "models/checkpoints/lgbm_day1.pkl"):
        self.model_path = model_path
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

        estimator = lgb.LGBMRegressor(objective='regression', metric='rmse', verbosity=-1)
        
        param_dist = {
            'learning_rate': [0.01, 0.05, 0.1],
            'num_leaves': [31, 64, 127],
            'bagging_fraction': [0.7, 0.8, 0.9],
            'feature_fraction': [0.7, 0.8, 0.9],
        }

        tscv = TimeSeriesSplit(n_splits=3)
        random_search = RandomizedSearchCV(
            estimator, param_distributions=param_dist,
            n_iter=5, cv=tscv, scoring='neg_root_mean_squared_error',
            random_state=42, n_jobs=-1
        )
        
        logger.info("Starting hyperparameter tuning via RandomizedSearchCV...")
        random_search.fit(X_aligned, y_valid)
        self.model = random_search.best_estimator_
        
        logger.info(f"Best params: {random_search.best_params_}")

        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def predict(self, feature_row: pd.DataFrame) -> float:
        """
        Predict return for tomorrow using ML + Agent Score Ensemble.
        """
        ml_pred = 0.0
        if self.model is not None:
            try:
                model_cols = self.model.feature_name_ if hasattr(self.model, "feature_name_") else self.feature_cols
                aligned = feature_row.copy()
                for col in model_cols:
                    if col not in aligned.columns:
                        aligned[col] = 0.0
                pred = self.model.predict(aligned[model_cols])
                ml_pred = float(pred[0])
            except Exception as e:
                logger.warning("Model predict failed (%s), fallback to 0.0.", e)
        
        return self._ensemble_prediction(feature_row, ml_pred)

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
        
        # 1 pt above neutral (5.0) contributes +0.2% return
        bandarm_effect = (bandarm_score - 5.0) * 0.002
        tech_effect = (tech_score - 5.0) * 0.001
        
        final_pred = ml_pred * 0.7 + bandarm_effect + tech_effect
        return final_pred

    def get_signal(self, pred_return: float) -> str:
        """
        Convert predicted return to signal string.
        """
        if pred_return >= 0.01: return "STRONG BUY"
        if pred_return >= 0.003: return "BUY"
        if pred_return <= -0.005: return "AVOID"
        return "HOLD"
