from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.funding.services.calculator import calculate_funding_plan, funding_score
from apps.policies.services.matcher import match_policies
from apps.products.services.matcher import match_products
from apps.recommendations.services.eligibility import eligibility_score


def location_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    preferred_regions = set(profile.get("preferred_regions", []))
    preferred_supply_types = set(profile.get("preferred_supply_types", []))

    score = 0
    score += 9 if notice.get("region") in preferred_regions else 0
    score += 3 if any(region and region in notice.get("district", "") for region in preferred_regions) else 0
    score += 3 if notice.get("supply_type") in preferred_supply_types or notice.get("housing_type") in preferred_supply_types else 0
    return min(score, 15)


def schedule_score(notice: dict[str, Any]) -> int:
    today = date.today()
    days_left = (datetime.fromisoformat(notice["application_deadline"]).date() - today).days
    contract_days = (datetime.fromisoformat(notice["contract_date"]).date() - today).days

    score = 0
    score += 3 if days_left >= 7 else 1 if days_left >= 0 else 0
    score += 5 if contract_days >= 30 else 2 if contract_days >= 0 else 0
    score += 2 if str(notice.get("move_in", "")) >= "2027-01" else 1
    return min(score, 10)


def policy_link_score(profile: dict[str, Any]) -> int:
    matched_products = match_products(profile, limit=10)
    matched_policies = match_policies(profile, limit=10)

    score = 0
    score += min(len(matched_products), 3) * 2
    score += min(len(matched_policies), 3) * 2
    score += 3 if any(product.get("protection_status") for product in matched_products) else 1
    return min(score, 15)


def score_detail(notice: dict[str, Any], profile: dict[str, Any]) -> dict[str, int]:
    return {
        "eligibility": eligibility_score(notice, profile),
        "funding": funding_score(notice, profile),
        "location": location_score(notice, profile),
        "schedule": schedule_score(notice),
        "policy_link": policy_link_score(profile),
    }


def score_reasons(notice: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    plan = calculate_funding_plan(notice, profile)
    return [
        f"{notice['region']} 희망 지역과 {notice['supply_type']} 선호 조건을 추천 점수에 반영했습니다.",
        f"계약금 예상액은 {plan['down_payment']:,}원이고 현재 준비 가능 현금은 {plan['available_cash']:,}원입니다.",
        f"부족액 {plan['shortfall']:,}원을 {plan['months_until_contract']}개월 기준 월 {plan['monthly_target']:,}원씩 준비해야 합니다.",
        "청년/생애최초 조건과 실제 접수 가능 여부는 공식 공고문에서 최종 확인해야 합니다.",
    ]
