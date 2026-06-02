from __future__ import annotations

from datetime import date
from typing import Any

from apps.fixture_store import default_profile, find_notice
from apps.rules.funding import (
    DEFAULT_CONTRACT_RATE,
    DEFAULT_MIDDLE_PAYMENT_RATE,
    available_cash,
    ceil_divide,
    default_payment_amounts,
    funding_score_from_plan,
)


def calculate_funding_plan(notice: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    price = int(notice["price"])
    price_confirmed = price > 0
    contract_rate = float(notice.get("contract_rate", DEFAULT_CONTRACT_RATE))
    payment_amounts = default_payment_amounts(
        price,
        contract_rate=contract_rate,
        middle_payment_rate=float(notice.get("middle_payment_rate", DEFAULT_MIDDLE_PAYMENT_RATE)),
    )
    down_payment = payment_amounts["down_payment"]
    cash = available_cash(profile)
    shortfall = max(0, down_payment - cash)
    months = max(int(profile.get("target_months", 1)), 1)
    monthly_target = ceil_divide(shortfall, months)
    middle_payment = payment_amounts["middle_payment"]
    final_payment = payment_amounts["final_payment"]

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
            "자금 로드맵은 참고용이며 실제 납부 조건은 공식 공고문과 계약 안내문에서 다시 확인해야 합니다."
            if price_confirmed
            else "분양가 또는 보증금 정보가 목록에 없어 자금 계산이 제한됩니다. 공식 공고문에서 금액을 확인해야 합니다."
        ),
    }


def calculate_option_funding_plan(option: Any, profile: dict[str, Any]) -> dict[str, Any]:
    notice = option.notice
    schedules = list(option.payment_schedules.all())
    down_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "down_payment")
    middle_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "middle_payment")
    final_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "final_payment")
    installment_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "installment_payment")
    price = int(option.base_price or 0)
    cash = available_cash(profile)
    shortfall = max(0, down_payment - cash)
    months = _months_until_down_payment(schedules, profile)
    monthly_target = ceil_divide(shortfall, months)
    loan_amount = int(getattr(option, "loan_amount", 0) or 0)
    timeline = [
        {
            "label": schedule.label,
            "date": schedule.due_date.isoformat() if schedule.due_date else "공식 확인 필요",
            "amount": schedule.amount,
            "payment_type": schedule.payment_type,
            "evidence_text": schedule.evidence_text,
        }
        for schedule in schedules
    ]
    if loan_amount > 0:
        timeline.append(
            {
                "label": "융자금",
                "date": "잔금 이후 상환",
                "amount": loan_amount,
                "payment_type": "loan",
                "evidence_text": "분양가에 포함된 융자금으로, 잔금 이후 기관 대출 조건에 따라 상환해야 합니다.",
            }
        )

    return {
        "notice_id": notice.id,
        "notice_title": notice.title,
        "option_id": option.id,
        "unit_type": option.unit_type,
        "exclusive_area_m2": option.exclusive_area_m2,
        "floor_group": option.floor_group,
        "option_type": option.option_type,
        "schedule_source": "payment_schedule",
        "price": price,
        "down_payment": down_payment,
        "middle_payment": middle_payment,
        "final_payment": final_payment,
        "installment_payment": installment_payment,
        "loan_amount": loan_amount,
        "available_cash": cash,
        "shortfall": shortfall,
        "months_until_contract": months,
        "monthly_target": monthly_target,
        "timeline": timeline,
        "notice": (
            "공식 공고문에서 추출한 주택형별 납부 일정 기준의 참고 계산입니다. "
            "실제 계약과 납부 조건은 기관 안내와 공고문 원문을 확인해야 합니다."
        ),
    }


def funding_plan(
    notice_id: int,
    profile: dict[str, Any] | None = None,
    *,
    option_id: int | None = None,
) -> dict[str, Any] | None:
    profile = profile or default_profile()
    option_plan = _option_funding_plan(option_id, notice_id, profile)
    if option_plan is not None:
        return option_plan

    notice = find_notice(notice_id)
    if notice is None:
        return None
    plan = calculate_funding_plan(notice, profile)
    plan["option_id"] = None
    plan["schedule_source"] = "notice"
    return plan


def funding_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    plan = calculate_funding_plan(notice, profile)
    return funding_score_from_plan(notice, profile, plan)


def _option_funding_plan(option_id: int | None, notice_id: int, profile: dict[str, Any]) -> dict[str, Any] | None:
    if not option_id:
        return None
    try:
        from apps.notice_docs.models import HousingUnitOption

        option = (
            HousingUnitOption.objects.select_related("notice")
            .prefetch_related("payment_schedules")
            .get(id=option_id, notice_id=notice_id)
        )
    except Exception:
        return None
    return calculate_option_funding_plan(option, profile)


def _months_until_down_payment(schedules: list[Any], profile: dict[str, Any]) -> int:
    down_payment_dates = [
        schedule.due_date
        for schedule in schedules
        if schedule.payment_type == "down_payment" and schedule.due_date
    ]
    if not down_payment_dates:
        return max(int(profile.get("target_months", 1)), 1)

    today = date.today()
    target_date = min(down_payment_dates)
    month_delta = (target_date.year - today.year) * 12 + target_date.month - today.month
    if target_date.day > today.day:
        month_delta += 1
    return max(month_delta, 1)
