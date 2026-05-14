#!/usr/bin/env python3
"""
Multi-Agent Voting Committee — Layer 4 -> Layer 6
Runs multiple agents in parallel, weighted voting for final signal
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CommitteeVote(BaseModel):
    """Individual agent vote"""
    agent_name: str
    trend: str  # bullish / bearish / neutral
    strength: int = Field(ge=1, le=10)
    confidence: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)


class CommitteeDecision(BaseModel):
    """Final committee decision"""
    final_trend: str
    consensus_score: float = Field(ge=0, le=1)
    total_agents: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    avg_strength: float


class VotingCommittee:
    """Weighted voting committee for agent signal fusion"""

    def __init__(self):
        # Agent name -> weight (updated by Bayesian engine in Phase 3)
        self.weights = {
            "technical_agent": 1.0,
            "news_agent": 0.8,
            "industry_agent": 0.6,
        }

    def update_weight(self, agent_name: str, new_weight: float):
        """Update an agent's voting weight"""
        self.weights[agent_name] = max(0.1, min(2.0, new_weight))
        logger.info(f"Weight updated: {agent_name} -> {new_weight:.2f}")

    def vote(self, votes: list[CommitteeVote]) -> CommitteeDecision:
        """Run weighted voting on agent votes"""
        if not votes:
            return CommitteeDecision(
                final_trend="neutral", consensus_score=0,
                total_agents=0, bullish_count=0,
                bearish_count=0, neutral_count=0, avg_strength=0,
            )

        # Apply weights
        weighted_scores = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
        total_weight = 0
        total_strength = 0

        for v in votes:
            w = self.weights.get(v.agent_name, 1.0) * v.confidence
            weighted_scores[v.trend] += w * v.strength
            total_weight += w
            total_strength += v.strength

        # Determine winner
        final_trend = max(weighted_scores, key=weighted_scores.get)
        max_score = weighted_scores[final_trend]
        consensus = min(1.0, max_score / (total_weight * 10 + 0.001))

        counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        for v in votes:
            counts[v.trend] += 1

        return CommitteeDecision(
            final_trend=final_trend,
            consensus_score=round(consensus, 3),
            total_agents=len(votes),
            bullish_count=counts["bullish"],
            bearish_count=counts["bearish"],
            neutral_count=counts["neutral"],
            avg_strength=round(total_strength / len(votes), 1),
        )
