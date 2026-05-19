from __future__ import annotations

from datetime import date, datetime
from typing import Any

from apps.fixture_store import default_profile, find_notice


def available_cash(profile: dict[str, Any]) -> int:
    """MVP 기준: debt는 참고 정보이고 계약금 준비 현금은 asset을 그대로 사용한다."""
    return max(0, int(profile.get("asset", 0)))


def calculate_funding_plan(notice: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    price = int(notice["price"])
    price_confirmed = price > 0
    contract_rate = float(notice.get("contract_rate", 0.1))
    down_payment = round(price * contract_rate)
    cash = available_cash(profile)
    shortfall = max(0, down_payment - cash)
    months = max(int(profile.get("target_months", 1)), 1)
    monthly_target = -(-shortfall // months)

    middle_payment = round(price * float(notice.get("middle_payment_rate", 0.6)))
    final_payment = max(0, price - down_payment - middle_payment)

    return {
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "price": price,
        "down_payment": down_payment,
        "available_cash": cash,
        "shortfall": shortfall,
        "months_until_contract": months,
        "monthly_target": monthly_target,
        "timeline": [
            {"label": "청약 접수 마감", "date": notice["application_deadline"], "amount": 0},
            {"label": "당첨자 발표", "date": notice["winner_date"], "amount": 0},
            {"label": "계약금 납부", "date": notice["contract_date"], "amount": down_payment},
            {"label": "중도금 계획 확인", "date": notice["contract_date"], "amount": middle_payment},
            {"label": "잔금 계획 확인", "date": notice["move_in"], "amount": final_payment},
        ],
        "notice": (
            "자금 로드맵은 참고용이며 실제 납부 조건은 공식 공고를 확인해야 합니다."
            if price_confirmed
            else "분양가 또는 보증금 정보가 API 목록에 없어 자금 계산은 제한됩니다. 공식 공고문에서 금액을 확인해야 합니다."
        ),
    }


def funding_plan(notice_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any] | None:
    notice = find_notice(notice_id)
    if notice is None:
        return None
    return calculate_funding_plan(notice, profile or default_profile())


def funding_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    plan = calculate_funding_plan(notice, profile)
    down_payment = plan["down_payment"]
    if down_payment <= 0:
        return 10
    readiness_ratio = min(plan["available_cash"] / down_payment if down_payment else 1, 1)
    saving = int(profile.get("monthly_saving", 0))
    target_months = max(int(profile.get("target_months", 1)), 1)
    contract_days = (
        datetime.fromisoformat(notice["contract_date"]).date() - date.today()
    ).days

    score = 0
    score += round(readiness_ratio * 10)
    score += 5 if plan["shortfall"] <= 30000000 else 3 if plan["shortfall"] <= 50000000 else 1
    score += 7 if plan["monthly_target"] <= saving else 4 if plan["monthly_target"] <= saving * 1.5 else 1
    score += 3 if target_months >= 12 and contract_days >= 30 else 1
    return min(score, 25)
