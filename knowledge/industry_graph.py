#!/usr/bin/env python3
"""
Industry Chain Graph — Layer 3 (lightweight, PostgreSQL-based)
Maps industry relationships without Neo4j
"""

import json, logging
from typing import Optional

logger = logging.getLogger(__name__)

# Manual industry chain data
INDUSTRY_CHAINS = {
    "ev": {
        "name": "Electric Vehicle",
        "upstream": ["lithium", "cobalt", "battery_manufacturing"],
        "midstream": ["motor", "controller", "chassis", "battery_pack"],
        "downstream": ["ev_assembly", "charging_infrastructure", "battery_recycling"],
        "companies": {
            "TSLA": {"sector": "ev_assembly", "suppliers": ["lithium", "battery_manufacturing"]},
            "BYD": {"sector": "ev_assembly", "suppliers": ["battery_manufacturing", "motor"]},
            "CATL": {"sector": "battery_manufacturing", "customers": ["ev_assembly"]},
        }
    },
    "semiconductor": {
        "name": "Semiconductor",
        "upstream": ["silicon_wafer", "chemicals", "equipment"],
        "midstream": ["chip_design", "fabrication"],
        "downstream": ["consumer_electronics", "automotive", "cloud_computing"],
        "companies": {
            "NVDA": {"sector": "chip_design", "customers": ["cloud_computing", "automotive"]},
            "TSM": {"sector": "fabrication", "suppliers": ["silicon_wafer", "equipment"]},
            "AMD": {"sector": "chip_design", "customers": ["consumer_electronics"]},
        }
    },
    "crypto_mining": {
        "name": "Crypto Mining",
        "upstream": ["asic_chip", "power_supply", "cooling"],
        "midstream": ["mining_rig", "mining_pool"],
        "downstream": ["btc_mining", "eth_staking"],
        "companies": {}
    }
}


class IndustryGraph:
    """Industry chain knowledge graph (lightweight)"""

    def get_chain(self, industry: str) -> Optional[dict]:
        return INDUSTRY_CHAINS.get(industry)

    def get_company_chain(self, company: str) -> Optional[dict]:
        """Find which industry chains a company belongs to"""
        for ind_name, ind_data in INDUSTRY_CHAINS.items():
            companies = ind_data.get("companies", {})
            if company.upper() in companies:
                return {
                    "industry": ind_name,
                    "industry_name": ind_data["name"],
                    "company_info": companies[company.upper()],
                    "upstream": ind_data["upstream"],
                    "downstream": ind_data["downstream"],
                }
        return None

    def find_affected(self, company: str, news_type: str) -> list[dict]:
        """
        Find companies affected by a news event
        news_type: "positive" / "negative"
        """
        result = []
        info = self.get_company_chain(company)
        if not info:
            return result

        multiplier = 1 if news_type == "positive" else -1
        industry = info["industry"]
        chain = INDUSTRY_CHAINS[industry]

        for other, details in chain.get("companies", {}).items():
            if other == company.upper():
                continue
            # Check if suppliers/customers relationship
            shared_suppliers = set(info["company_info"].get("suppliers", [])) &                                set(details.get("suppliers", []))
            shared_customers = set(info["company_info"].get("customers", [])) &                                set(details.get("customers", []))
            if shared_suppliers or shared_customers:
                impact = "positive" if multiplier > 0 else "negative"
                if shared_suppliers:
                    impact = "positive" if multiplier > 0 else "negative"
                result.append({
                    "company": other,
                    "relationship": "supplier" if shared_suppliers else "customer",
                    "impact": impact,
                    "strength": min(1.0, (len(shared_suppliers) + len(shared_customers)) / 3),
                })
        return result
