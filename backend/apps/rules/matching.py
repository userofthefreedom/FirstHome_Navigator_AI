from __future__ import annotations

import re
from datetime import date
from typing import Any

from apps.rules.funding import effective_monthly_capacity
from apps.rules.regions import infer_region_from_text, region_matches


POLICY_MATCH_FIXTURE_PENALTY = 6


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


def product_match_score(product: dict[str, Any], profile: dict[str, Any]) -> int:
    target_months = max(int(profile.get("target_months", 0) or 0), 0)
    monthly_saving = max(int(effective_monthly_capacity(profile) or 0), 0)
    term_months = _product_term_months(product)
    monthly_limit = max(int(product.get("monthly_limit", 0) or 0), 0)

    score = 0
    score += _product_term_score(term_months, target_months)
    score += _product_monthly_limit_score(monthly_limit, monthly_saving)
    score += _product_rate_score(_product_best_rate(product))
    score += _product_category_score(product)
    score += min(5, _product_option_count(product))
    if product.get("protection_status"):
        score += 3
    if product.get("source_url"):
        score += 3
    if _product_name_has_planning_hint(product):
        score += 2
    return max(0, min(100, int(round(score))))


def _product_term_months(product: dict[str, Any]) -> int:
    term_months = int(product.get("term_months", 0) or 0)
    if term_months:
        return term_months
    best_option = product.get("best_option")
    if isinstance(best_option, dict):
        return int(best_option.get("save_trm") or 0)
    return 0


def _product_term_score(term_months: int, target_months: int) -> int:
    if not term_months or not target_months:
        return 7 if term_months else 4
    diff = abs(term_months - target_months)
    if diff == 0:
        return 20
    if diff <= 3:
        return 18
    if diff <= 6:
        return 15
    if diff <= 12:
        return 10
    if diff <= 18:
        return 6
    return 3


def _product_monthly_limit_score(monthly_limit: int, monthly_saving: int) -> int:
    if monthly_saving <= 0:
        return 11
    if monthly_limit <= 0:
        return 14
    ratio = monthly_limit / monthly_saving
    if ratio >= 1:
        return 18
    if ratio >= 0.8:
        return 14
    if ratio >= 0.6:
        return 10
    if ratio >= 0.4:
        return 6
    return 2


def _product_best_rate(product: dict[str, Any]) -> float:
    candidates: list[Any] = [product.get("rate")]
    best_option = product.get("best_option")
    if isinstance(best_option, dict):
        candidates.extend([best_option.get("intr_rate2"), best_option.get("intr_rate")])
    for option in product.get("options") or []:
        if isinstance(option, dict):
            candidates.extend([option.get("intr_rate2"), option.get("intr_rate")])
    return max((_parse_rate(value) for value in candidates), default=0.0)


def _parse_rate(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0.0


def _product_rate_score(rate: float) -> int:
    if rate <= 0:
        return 0
    return min(55, max(4, int(round(rate * 10))))


def _product_category_score(product: dict[str, Any]) -> int:
    category = str(product.get("category") or "").lower()
    if any(keyword in category for keyword in ("saving", "적금", "청약")):
        return 8
    if any(keyword in category for keyword in ("deposit", "예금")):
        return 6
    return 4


def _product_option_count(product: dict[str, Any]) -> int:
    explicit_count = int(product.get("option_count") or 0)
    if explicit_count:
        return explicit_count
    options = product.get("options") or []
    if isinstance(options, list) and options:
        return len(options)
    return 1 if _product_term_months(product) else 0


def _product_name_has_planning_hint(product: dict[str, Any]) -> bool:
    searchable = f"{product.get('name') or ''} {product.get('provider') or ''}"
    return any(keyword in searchable for keyword in ("청년", "내집", "주거", "주택", "직장인"))


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

    age = date.today().year - int(profile.get("birth_year", date.today().year) or date.today().year)
    income = int(profile.get("annual_income", 0) or 0)
    preferred_regions = [str(region or "").strip() for region in profile.get("preferred_regions", []) if str(region or "").strip()]
    is_homeless = bool(profile.get("is_homeless"))

    score = 0
    if int(policy.get("age_min", 0)) <= age <= int(policy.get("age_max", 150)):
        score += 18
    max_income = int(policy.get("max_income", 0) or 0)
    if max_income <= 0 or income <= max_income:
        score += 12 if max_income <= 0 else 18
    policy_regions = _policy_regions(policy)
    has_specific_region_match = any(
        _region_matches(policy_region, preferred_region)
        for policy_region in policy_regions
        for preferred_region in preferred_regions
    )
    if has_specific_region_match:
        score += 28
    elif "전국" in policy_regions:
        score += 14
    if not policy.get("requires_homeless") or is_homeless:
        score += 16 if policy.get("requires_homeless") else 10
    if policy.get("policy_category") in {"월세", "전세", "주거지원", "상담", "주거"}:
        score += 8
    if policy.get("source_url"):
        score += 5
    if _policy_has_purchase_or_subscription_signal(policy):
        score += 7
    if _is_fixture_policy(policy):
        score = max(0, score - POLICY_MATCH_FIXTURE_PENALTY)
    source_priority = 1 if "온통청년" in str(policy.get("data_source", "")) else 0
    return max(0, min(100, score)), source_priority


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


def _policy_regions(policy: dict[str, Any]) -> list[str]:
    policy_regions = [str(region or "").strip() for region in policy.get("regions", []) if str(region or "").strip()]
    if policy_regions and "전국" not in policy_regions:
        return policy_regions
    inferred_regions = _infer_policy_regions(policy)
    return inferred_regions or policy_regions


def _is_fixture_policy(policy: dict[str, Any]) -> bool:
    return "fixture" in str(policy.get("data_source", "")).lower()


def _policy_has_purchase_or_subscription_signal(policy: dict[str, Any]) -> bool:
    searchable_text = " ".join(
        str(policy.get(field) or "")
        for field in ("name", "provider", "target", "benefit", "policy_category")
    )
    return any(keyword in searchable_text for keyword in ("청약", "분양", "주택구입", "구입자금", "내집", "첫집", "주택자금"))


def _infer_policy_regions(policy: dict[str, Any]) -> list[str]:
    searchable_text = " ".join(
        str(policy.get(field) or "")
        for field in ("name", "provider", "target", "benefit")
    )
    return infer_region_from_text(searchable_text)

