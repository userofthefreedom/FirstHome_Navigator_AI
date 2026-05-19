from __future__ import annotations

from typing import Any

from apps.ai_coach.services.safety_filter import sanitize_summary
from apps.fixture_store import default_profile, find_notice
from apps.funding.services.calculator import funding_plan
from apps.recommendations.services.ranking import calculate_score


def coach_summary(notice_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile)
    if notice is None or plan is None:
        return None

    recommendation = calculate_score(notice, profile)
    summary = {
        "source": "template_fallback",
        "summary": (
            f"{notice['title']}은(는) {notice['region']} 희망 지역과 {notice['supply_type']} 조건이 잘 맞는 후보입니다. "
            f"총점은 {recommendation['total_score']}점이며 계약금 기준 부족액은 {plan['shortfall']:,}원입니다. "
            f"월 {plan['monthly_target']:,}원 수준의 준비 계획을 세우되 공식 공고의 자격 기준을 다시 확인하세요."
        ),
        "todo_this_week": [
            "주민등록등본, 소득금액증명원, 청약통장 가입확인서 발급 가능 여부를 확인하세요.",
            f"{notice['provider']} 또는 공식 청약 사이트에서 청년/생애최초 세부 조건을 확인하세요.",
            "계약금으로 사용할 현금과 생활비 계좌를 분리해 관리하세요.",
        ],
        "official_checklist": [
            "무주택 및 세대 구성 기준",
            "소득, 자산, 청약통장 납입 인정 기준",
            "접수 마감일, 계약일, 분양가와 납부 일정",
        ],
        "warning": "추천 결과는 공개 데이터와 fixture 기반 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다.",
    }
    return sanitize_summary(summary)
