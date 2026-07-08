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
from data.ml_features import ML_TRAIN_FEATURES

logger = logging.getLogger(__name__)

class MultiDayPredictor:
    def __init__(self, ticker: str = "GLOBAL", checkpoints_dir: str = "models/checkpoints"):
        self.ticker = ticker.upper()
        self.checkpoints_dir = checkpoints_dir
        self.feature_cols = ML_TRAIN_FEATURES
        self.horizons = ['1d', '3d', '5d', '7d']
        self.models = {h: None for h in self.horizons}

        self._load_models()

    def _get_model_path(self, horizon: str) -> str:
        return os.path.join(self.checkpoints_dir, f"lgbm_{self.ticker}_{horizon}.pkl")

    def _load_models(self):
        for h in self.horizons:
            path = self._get_model_path(h)
            if os.path.exists(path):
                try:
                    self.models[h] = joblib.load(path)
                except Exception as e:
                    logger.debug(f"Failed to load {h} model for {self.ticker}: {e}")

    def train_incremental(self, X_train: pd.DataFrame, Y_targets_train: pd.DataFrame, X_val: pd.DataFrame = None, Y_targets_val: pd.DataFrame = None):
        """
        Train 4 independent models for 1d, 3d, 5d, and 7d horizons with early stopping.
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
            y_tr = y_train[valid_idx].astype(float)

            # Time-decay sample weights
            n_samples = len(X_tr)
            decay_factor = 3.0
            weights = np.exp(np.linspace(0, np.log(decay_factor), n_samples))
            weights = weights / weights.mean()

            params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'verbosity': -1,
                'boosting_type': 'gbdt',
                'learning_rate': 0.05,
                'num_leaves': 31,
                'min_child_samples': 20,
                'bagging_fraction': 0.8,
                'feature_fraction': 0.8,
                'bagging_freq': 1,
                'seed': 42
            }

            dtrain = lgb.Dataset(X_tr, label=y_tr, weight=weights)
            
            valid_sets = [dtrain]
            callbacks = []

            if X_val_aligned is not None and Y_targets_val is not None and col_name in Y_targets_val.columns:
                y_val = Y_targets_val[col_name]
                val_valid_idx = ~y_val.isna()
                if val_valid_idx.any():
                    X_v = X_val_aligned[val_valid_idx].copy()
                    y_v = y_val[val_valid_idx].astype(float)
                    dval = lgb.Dataset(X_v, label=y_v, reference=dtrain)
                    valid_sets.append(dval)
                    callbacks.append(lgb.early_stopping(stopping_rounds=20, verbose=False))
            
            logger.debug(f"Training {self.ticker} horizon: {h} on {len(X_tr)} samples")
            
            # Using lgb.train directly instead of scikit-learn API for native early stopping and callbacks
            callbacks.append(lgb.log_evaluation(period=0)) # suppress output
            self.models[h] = lgb.train(
                params, 
                dtrain, 
                num_boost_round=300,
                valid_sets=valid_sets,
                callbacks=callbacks
            )

            # Save model
            model_path = self._get_model_path(h)
            joblib.dump(self.models[h], model_path)

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
        Uses original linear logic but maps to a probability [0.0, 1.0].
        """
        score = (
            feature_row['bandarm_score'].iloc[0] * 0.4 +
            feature_row['technical_score'].iloc[0] * 0.3 +
            (1.0 if feature_row['is_bullish_trend'].iloc[0] > 0.5 else -0.5) * 0.2 +
            feature_row['macro_score'].iloc[0] * 0.1
        )
        # Map 1-10 score to roughly 0.40 to 0.60 probability
        prob = 0.50 + (score - 5.5) * 0.02
        return max(0.0, min(1.0, prob))

    def get_signal(self, pred_prob_1d: float) -> str:
        """
        Convert predicted 1d probability to signal string.
        """
        if pred_prob_1d >= 0.55: return "STRONG BUY"
        if pred_prob_1d >= 0.51: return "BUY"
        if pred_prob_1d <= 0.48: return "AVOID"
        return "HOLD"
