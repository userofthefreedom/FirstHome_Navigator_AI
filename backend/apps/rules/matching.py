from __future__ import annotations

from datetime import date
from typing import Any

from apps.rules.funding import effective_monthly_capacity
from apps.rules.regions import REGION_ALIASES, normalize_region_key, region_matches


FIXTURE_POLICY_SCORE_PENALTY = 2


DIRECT_HOUSING_POLICY_CATEGORIES = {
    "청약",
    "주거",
    "주거지원",
    "월세",
    "전세",
    "보증금",
    "부동산",
    "임대",
    "공공주택",
}
HOUSING_POLICY_KEYWORDS = {
    "청약",
    "주거",
    "주택",
    "공공분양",
    "분양",
    "월세",
    "전세",
    "보증금",
    "임차보증금",
    "임대",
    "주택구입",
    "구입자금",
    "주택담보",
    "내집",
    "첫집",
    "부동산",
}
NON_USER_HOUSING_POLICY_KEYWORDS = {
    "창업자",
    "창업가",
    "사업장",
    "점포",
    "상가",
    "보행환경",
    "도로",
    "거리 조성",
    "환경 개선",
    "정비사업",
}
POLICY_REGION_ALIASES = REGION_ALIASES


def product_match_score(product: dict[str, Any], profile: dict[str, Any]) -> int:
    target_months = int(profile.get("target_months", 0))
    monthly_saving = effective_monthly_capacity(profile)
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


def is_housing_related_policy(policy: dict[str, Any]) -> bool:
    category = str(policy.get("policy_category") or "").strip()
    searchable_text = " ".join(
        str(policy.get(field) or "")
        for field in ("name", "provider", "target", "benefit", "policy_category", "data_source")
    )
    if any(keyword in searchable_text for keyword in NON_USER_HOUSING_POLICY_KEYWORDS):
        return False
    if category in DIRECT_HOUSING_POLICY_CATEGORIES:
        return True
    return any(keyword in searchable_text for keyword in HOUSING_POLICY_KEYWORDS)


def policy_match_score(policy: dict[str, Any], profile: dict[str, Any]) -> tuple[int, int]:
    if not is_housing_related_policy(policy):
        return 0, 0
    if not is_policy_region_relevant(policy, profile):
        return 0, 0

    age = date.today().year - int(profile.get("birth_year", date.today().year))
    income = int(profile.get("annual_income", 0))
    preferred_regions = [str(region or "").strip() for region in profile.get("preferred_regions", []) if str(region or "").strip()]
    is_homeless = bool(profile.get("is_homeless"))

    score = 0
    if int(policy.get("age_min", 0)) <= age <= int(policy.get("age_max", 150)):
        score += 4
    max_income = int(policy.get("max_income", 0) or 0)
    if max_income <= 0 or income <= max_income:
        score += 3
    policy_regions = _policy_regions(policy)
    has_specific_region_match = any(
        _region_matches(policy_region, preferred_region)
        for policy_region in policy_regions
        for preferred_region in preferred_regions
    )
    if has_specific_region_match:
        score += 4
    elif "전국" in policy_regions:
        score += 2
    if not policy.get("requires_homeless") or is_homeless:
        score += 2
    if policy.get("policy_category") in {"월세", "전세", "주거지원", "상담", "주거"}:
        score += 1
    if policy.get("source_url"):
        score += 1
    if _is_fixture_policy(policy):
        score = max(0, score - FIXTURE_POLICY_SCORE_PENALTY)
    source_priority = 1 if "온통청년" in str(policy.get("data_source", "")) else 0
    return score, source_priority


def is_policy_region_relevant(policy: dict[str, Any], profile: dict[str, Any]) -> bool:
    policy_regions = _policy_regions(policy)
    preferred_regions = [str(region or "").strip() for region in profile.get("preferred_regions", []) if str(region or "").strip()]
    if "전국" in policy_regions:
        return True
    if not preferred_regions:
        return False

    return any(
        _region_matches(policy_region, preferred_region)
        for policy_region in policy_regions
        for preferred_region in preferred_regions
    )


def _region_matches(target_region: str, preferred_region: str) -> bool:
    return region_matches(target_region, preferred_region)


def _normalize_region_key(value: Any) -> str:
    return normalize_region_key(value)


def _policy_regions(policy: dict[str, Any]) -> list[str]:
    policy_regions = [str(region or "").strip() for region in policy.get("regions", []) if str(region or "").strip()]
    inferred_regions = _infer_policy_regions(policy)
    return inferred_regions or policy_regions


def _is_fixture_policy(policy: dict[str, Any]) -> bool:
    return "fixture" in str(policy.get("data_source", "")).lower()


def _infer_policy_regions(policy: dict[str, Any]) -> list[str]:
    searchable_text = " ".join(
        str(policy.get(field) or "")
        for field in ("name", "provider", "target", "benefit")
    )
    text_key = _normalize_region_key(searchable_text)
    matched = [
        canonical
        for canonical, aliases in POLICY_REGION_ALIASES.items()
        if any(
            _normalize_region_key(alias) in text_key
            for alias in aliases
            if len(_normalize_region_key(alias)) >= 3
        )
    ]
    return matched

