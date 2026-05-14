#!/usr/bin/env python3
"""
HMM Market State Recognition — Layer 2 (pure Python)
Identifies hidden market regimes using hmmlearn
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn not installed. HMM unavailable.")


class HMMRegimeDetector:
    """Hidden Markov Model for market regime identification"""

    def __init__(self, n_states: int = 3, n_iter: int = 100):
        self.n_states = n_states
        self.n_iter = n_iter
        self.model = None
        self.state_names = {0: "sideways", 1: "bull", 2: "bear"}

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix for HMM"""
        close = df['close'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        vol = df['volume'].astype(float)

        # Returns
        returns = close.pct_change().fillna(0)

        # Volatility (20-day rolling)
        volatility = returns.rolling(20).std().fillna(0)

        # Volume change
        vol_change = vol.pct_change().fillna(0)

        features = pd.DataFrame({
            "return": returns,
            "volatility": volatility,
            "vol_change": vol_change,
        }).dropna()

        # Clip extreme values
        for col in features.columns:
            features[col] = features[col].clip(-0.1, 0.1)

        return features.values

    def fit(self, df: pd.DataFrame):
        """Train HMM on historical data"""
        if not HMM_AVAILABLE:
            logger.warning("HMM unavailable, using rule-based fallback")
            return

        X = self._prepare_features(df)
        if len(X) < self.n_states * 10:
            logger.warning(f"Too few samples ({len(X)}) for HMM")
            return

        self.model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=self.n_iter,
            random_state=42,
        )
        self.model.fit(X)

        # Infer state names by mean return
        means = np.mean(self.model.means_, axis=2).flatten() if len(self.model.means_.shape) > 2 else                 self.model.means_[:, 0]
        sorted_idx = np.argsort(means)
        self.state_names = {
            sorted_idx[0]: "bear",
            sorted_idx[1]: "sideways",
            sorted_idx[2]: "bull",
        } if self.n_states >= 3 else {
            sorted_idx[0]: "bear",
            sorted_idx[1]: "bull",
        }
        logger.info(f"HMM trained: {self.n_states} states")

    def predict(self, df: pd.DataFrame) -> dict:
        """Predict current market regime"""
        if self.model is None:
            return {"regime": "unknown", "probabilities": {}, "description": "model not trained"}

        X = self._prepare_features(df)
        if len(X) == 0:
            return {"regime": "unknown", "probabilities": {}, "description": "no features"}

        states = self.model.predict(X)
        probs = self.model.predict_proba(X)

        current_state = int(states[-1])
        current_probs = probs[-1]

        regime = self.state_names.get(current_state, "unknown")
        prob_dict = {self.state_names.get(i, f"s{i}"): round(float(p), 3)
                     for i, p in enumerate(current_probs)}

        return {
            "regime": regime,
            "probabilities": prob_dict,
            "description": f"HMM predicts: {regime} "
                           f"(confidence: {max(current_probs):.1%})",
        }
