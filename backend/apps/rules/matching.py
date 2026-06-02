from __future__ import annotations

from datetime import date
from typing import Any


def product_match_score(product: dict[str, Any], profile: dict[str, Any]) -> int:
    target_months = int(profile.get("target_months", 0))
    monthly_saving = int(profile.get("monthly_saving", 0))
    term_months = int(product.get("term_months", 0))
    monthly_limit = int(product.get("monthly_limit", 0))
    protected = bool(product.get("protection_status"))

    score = 0
    if term_months and abs(term_months - target_months) <= 6:
        score += 4
    elif term_months and term_months <= max(target_months, 1) + 12:
        score += 2
    if monthly_limit == 0 or monthly_limit >= monthly_saving:
        score += 3
    elif monthly_limit >= monthly_saving * 0.7:
        score += 2
    if product.get("category") in {"적금", "청약통장"}:
        score += 2
    if protected:
        score += 1
    if product.get("source_url"):
        score += 1
    return score


def policy_match_score(policy: dict[str, Any], profile: dict[str, Any]) -> tuple[int, int]:
    age = date.today().year - int(profile.get("birth_year", date.today().year))
    income = int(profile.get("annual_income", 0))
    preferred_regions = set(profile.get("preferred_regions", []))
    is_homeless = bool(profile.get("is_homeless"))

    score = 0
    if int(policy.get("age_min", 0)) <= age <= int(policy.get("age_max", 150)):
        score += 4
    max_income = int(policy.get("max_income", 0) or 0)
    if max_income <= 0 or income <= max_income:
        score += 3
    policy_regions = set(policy.get("regions", []))
    if "전국" in policy_regions or preferred_regions & policy_regions:
        score += 3
    if not policy.get("requires_homeless") or is_homeless:
        score += 2
    if policy.get("policy_category") in {"월세", "전세", "주거지원", "상담", "주거"}:
        score += 1
    if policy.get("source_url"):
        score += 1
    source_priority = 1 if "온통청년" in str(policy.get("data_source", "")) else 0
    return score, source_priority

