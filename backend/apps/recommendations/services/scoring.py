from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.funding.services.calculator import calculate_funding_plan, funding_score
from apps.recommendations.services.eligibility import eligibility_score


SCORE_WEIGHTS = {
    "eligibility": 35,
    "funding": 25,
    "location": 30,
    "schedule": 10,
}


def location_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    preferred_regions = set(profile.get("preferred_regions", []))
    preferred_supply_types = set(profile.get("preferred_supply_types", []))

    score = 0
    score += 18 if notice.get("region") in preferred_regions else 0
    score += 6 if any(region and region in notice.get("district", "") for region in preferred_regions) else 0
    score += 6 if notice.get("supply_type") in preferred_supply_types or notice.get("housing_type") in preferred_supply_types else 0
    return min(score, SCORE_WEIGHTS["location"])


def schedule_score(notice: dict[str, Any]) -> int:
    today = date.today()
    days_left = (datetime.fromisoformat(notice["application_deadline"]).date() - today).days
    contract_days = (datetime.fromisoformat(notice["contract_date"]).date() - today).days

    score = 0
    score += 3 if days_left >= 7 else 1 if days_left >= 0 else 0
    score += 5 if contract_days >= 30 else 2 if contract_days >= 0 else 0
    score += 2 if str(notice.get("move_in", "")) >= "2027-01" else 1
    return min(score, 10)


def score_detail(notice: dict[str, Any], profile: dict[str, Any]) -> dict[str, int]:
    return {
        "eligibility": eligibility_score(notice, profile),
        "funding": funding_score(notice, profile),
        "location": location_score(notice, profile),
        "schedule": schedule_score(notice),
    }


def score_max() -> int:
    return sum(SCORE_WEIGHTS.values())


def score_reasons(notice: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    plan = calculate_funding_plan(notice, profile)
    if int(notice.get("price") or 0) <= 0:
        return [
            f"{notice['region']} 지역의 {notice['supply_type']} 공고로 희망 조건과의 적합도를 계산했습니다.",
            "API 목록에 분양가 또는 보증금이 없어 자금 점수는 중립값으로 반영했습니다.",
            "세부 자격, 금액, 계약 일정은 공식 공고문에서 최종 확인해야 합니다.",
        ]
    return [
        f"{notice['region']} 희망 지역과 {notice['supply_type']} 선호 조건을 추천 점수에 반영했습니다.",
        f"계약금 예상액은 {plan['down_payment']:,}원이고 현재 준비 가능 현금은 {plan['available_cash']:,}원입니다.",
        f"부족액 {plan['shortfall']:,}원을 {plan['months_until_contract']}개월 기준 월 {plan['monthly_target']:,}원씩 준비해야 합니다.",
        "청년/생애최초 조건과 실제 접수 가능 여부는 공식 공고문에서 최종 확인해야 합니다.",
    ]
