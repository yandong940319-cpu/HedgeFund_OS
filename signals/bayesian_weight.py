#!/usr/bin/env python3
"""
Bayesian Dynamic Weight Engine — Layer 6
Updates agent weights based on historical review performance
Uses Beta-Binomial conjugate model for robust estimation
"""

import json, logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BayesianWeightEngine:
    def __init__(self):
        self.priors = {}  # agent_name -> {alpha, beta}

    def _get_posterior_mean(self, agent: str, successes: int, trials: int) -> float:
        """Beta posterior mean: (alpha + successes) / (alpha + beta + trials)"""
        alpha0, beta0 = self.priors.get(agent, (1, 1))
        alpha = alpha0 + successes
        beta = beta0 + (trials - successes)
        self.priors[agent] = (alpha, beta)
        return alpha / (alpha + beta)

    def update_from_reviews(self, reviews: list[dict]) -> dict[str, float]:
        """
        Update weights from review_logs data.
        reviews: [{agent_name, correct}]
        Returns: {agent_name: new_weight}
        """
        stats = {}
        for r in reviews:
            agent = r.get("agent_name", "unknown")
            correct = r.get("correct", False)
            if agent not in stats:
                stats[agent] = {"successes": 0, "trials": 0}
            stats[agent]["trials"] += 1
            if correct:
                stats[agent]["successes"] += 1

        weights = {}
        for agent, s in stats.items():
            w = self._get_posterior_mean(agent, s["successes"], s["trials"])
            # Scale to 0.1-2.0 range
            weights[agent] = round(0.1 + w * 1.9, 3)
            logger.info(f"Weight updated: {agent} -> {weights[agent]} "
                        f"({s['successes']}/{s['trials']} correct)")

        return weights

    def get_weight(self, agent: str, default: float = 1.0) -> float:
        """Get current weight for an agent"""
        if agent in self.priors:
            alpha, beta = self.priors[agent]
            return round(0.1 + (alpha / (alpha + beta)) * 1.9, 3)
        return default

    def load_from_db(self):
        """Load review data from PostgreSQL and update weights"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname='hedgefund', user='admin', password='Passw0rd',
                host='localhost', port=5432
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT agent_name, correct FROM review_logs "
                "WHERE created_at > NOW() - INTERVAL '30 days'"
            )
            reviews = [{"agent_name": r[0], "correct": r[1]} for r in cur.fetchall()]
            cur.close()
            conn.close()
            if reviews:
                return self.update_from_reviews(reviews)
            return {}
        except Exception as e:
            logger.error(f"Failed to load reviews: {e}")
            return {}
