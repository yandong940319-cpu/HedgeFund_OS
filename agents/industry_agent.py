#!/usr/bin/env python3
"""
Industry Chain Analysis Agent — Layer 4
Analyzes how news/events affect industry chains
"""

import os, json, logging
from typing import Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)

from knowledge.industry_graph import IndustryGraph


class IndustryImpact(BaseModel):
    company: str
    impact: str  # positive / negative / neutral
    confidence: float = Field(ge=0, le=1)
    affected_sectors: list[str]
    reason: str = Field(max_length=300)


class IndustryAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.graph = IndustryGraph()

    def analyze(self, company: str, news_title: str,
                news_content: str = "") -> Optional[IndustryImpact]:
        """Analyze news impact on a company and its industry chain"""
        chain_info = self.graph.get_company_chain(company)
        affected = self.graph.find_affected(company, "positive")

        context = ""
        if chain_info:
            context = f"\nIndustry: {chain_info['industry_name']}\n"
            context += f"Sector: {chain_info['company_info'].get('sector', 'N/A')}\n"
            affected_names = [a["company"] for a in affected[:3]]
            if affected_names:
                context += f"Related companies: {', '.join(affected_names)}"

        prompt = (
            f"Analyze the impact of this news on {company}:\n\n"
            f"Title: {news_title}\n"
            f"Content: {news_content[:500]}\n{context}\n\n"
            "Output JSON:\n"
            '{"impact": "positive/negative/neutral", '
            '"confidence": 0-1, '
            '"affected_sectors": ["sector1", "sector2"], '
            '"reason": "analysis(max 300 chars)"}'
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=500,
            )
            result = json.loads(resp.choices[0].message.content
                                .split('```json')[-1].split('```')[0].strip())

            impact = IndustryImpact(
                company=company,
                impact=result.get("impact", "neutral"),
                confidence=result.get("confidence", 0.5),
                affected_sectors=result.get("affected_sectors", []),
                reason=result.get("reason", ""),
            )
            return impact
        except Exception as e:
            logger.error(f"Industry analysis failed {company}: {e}")
            return None
