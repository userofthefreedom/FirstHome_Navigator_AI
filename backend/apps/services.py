from __future__ import annotations

from apps.ai_coach.services.prompt_templates import coach_summary
from apps.fixture_store import default_profile, find_notice, notices, policies, products
from apps.funding.services.calculator import funding_plan
from apps.policies.services.matcher import match_policies
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import calculate_score, ranked_recommendations

__all__ = [
    "calculate_score",
    "coach_summary",
    "default_profile",
    "find_notice",
    "funding_plan",
    "match_policies",
    "match_products",
    "notices",
    "policies",
    "products",
    "ranked_recommendations",
]
