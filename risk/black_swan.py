#!/usr/bin/env python3
"""
Black Swan Detection — Layer 5
Uses Isolation Forest to detect anomalous market conditions
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def detect_anomaly(df: pd.DataFrame, contamination: float = 0.05) -> dict:
    """
    Detect anomalous market conditions using Isolation Forest.

    Args:
        df: DataFrame with close, high, low, volume columns
        contamination: Expected proportion of outliers

    Returns:
        {is_anomaly, anomaly_score, details}
    """
    if not SKLEARN_AVAILABLE:
        return {"is_anomaly": False, "anomaly_score": 0,
                "details": "sklearn not available"}

    if df.empty or len(df) < 20:
        return {"is_anomaly": False, "anomaly_score": 0,
                "details": "insufficient data"}

    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    vol = df['volume'].astype(float)

    # Feature engineering
    returns = close.pct_change().fillna(0)
    volatility = returns.rolling(10).std().fillna(0)
    vol_change = vol.pct_change().fillna(0)
    range_pct = (high - low) / close * 100

    features = pd.DataFrame({
        "return": returns,
        "volatility": volatility,
        "vol_change": vol_change,
        "range_pct": range_pct,
    }).dropna().values

    if len(features) < 10:
        return {"is_anomaly": False, "anomaly_score": 0,
                "details": "too few samples after dropna"}

    # Train on all data, predict on latest
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
    )
    model.fit(features)

    scores = model.score_samples(features)
    latest_score = float(scores[-1])
    # Convert to 0-1 anomaly score (more negative = more anomalous)
    anomaly_score = float(1 - (latest_score - scores.min()) / (scores.max() - scores.min() + 1e-9))

    prediction = int(model.predict(features[-1:])[0])
    is_anomaly = prediction == -1

    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 3),
        "sharpe_3d": round(float(returns[-3:].mean() / (returns[-3:].std() + 1e-9)), 2) if len(returns) >= 3 else 0,
        "details": f"{'ANOMALY DETECTED' if is_anomaly else 'Normal'} (score={anomaly_score:.2f})",
    }
