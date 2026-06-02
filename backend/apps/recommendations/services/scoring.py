from __future__ import annotations

from typing import Any

from apps.funding.services.calculator import calculate_funding_plan, funding_score
from apps.rules.scoring import SCORE_WEIGHTS, eligibility_score, location_score, schedule_score, score_max


def score_detail(notice: dict[str, Any], profile: dict[str, Any]) -> dict[str, int]:
    return {
        "eligibility": eligibility_score(notice, profile),
        "funding": funding_score(notice, profile),
        "location": location_score(notice, profile),
        "schedule": schedule_score(notice),
    }
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
