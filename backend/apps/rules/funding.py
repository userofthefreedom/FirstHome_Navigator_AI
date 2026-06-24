from __future__ import annotations

from datetime import date, datetime
from typing import Any


DEFAULT_CONTRACT_RATE = 0.1
DEFAULT_MIDDLE_PAYMENT_RATE = 0.6
SHORTFALL_LOW_WON = 30_000_000
SHORTFALL_MID_WON = 50_000_000
DEBT_CASH_RESERVE_RATE = 0.3
DEBT_MONTHLY_RESERVE_MONTHS = 60
JOB_STATUS_MONTHLY_CAPACITY_FACTOR = {
    "employed": 1.0,
    "self_employed": 0.95,
    "student": 0.9,
    "unemployed": 0.85,
}


def available_cash(profile: dict[str, Any]) -> int:
    return max(0, int(profile.get("asset", 0)) - debt_cash_reserve(profile))


def debt_cash_reserve(profile: dict[str, Any]) -> int:
    return round(max(0, int(profile.get("debt", 0))) * DEBT_CASH_RESERVE_RATE)


def debt_monthly_reserve(profile: dict[str, Any]) -> int:
    debt = max(0, int(profile.get("debt", 0)))
    return ceil_divide(debt, DEBT_MONTHLY_RESERVE_MONTHS) if debt else 0


def job_status_capacity_factor(profile: dict[str, Any]) -> float:
    job_status = str(profile.get("job_status") or "employed")
    return JOB_STATUS_MONTHLY_CAPACITY_FACTOR.get(job_status, 0.85)


def effective_monthly_capacity(profile: dict[str, Any]) -> int:
    raw_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)
    adjusted_by_job = round(raw_capacity * job_status_capacity_factor(profile))
    return max(0, adjusted_by_job - debt_monthly_reserve(profile))


def effective_down_payment_cash(profile: dict[str, Any]) -> int:
    raw_cash = int(profile.get("max_down_payment") or profile.get("asset") or 0)
    return max(0, raw_cash - debt_cash_reserve(profile))


def default_payment_amounts(price: int, *, contract_rate: float = DEFAULT_CONTRACT_RATE, middle_payment_rate: float = DEFAULT_MIDDLE_PAYMENT_RATE) -> dict[str, int]:
    down_payment = round(price * contract_rate)
    middle_payment = round(price * middle_payment_rate)
    final_payment = max(0, price - down_payment - middle_payment)
    return {
        "down_payment": down_payment,
        "middle_payment": middle_payment,
        "final_payment": final_payment,
    }


def ceil_divide(amount: int, divisor: int) -> int:
    divisor = max(int(divisor), 1)
    return -(-int(amount) // divisor)


def funding_score_from_plan(notice: dict[str, Any], profile: dict[str, Any], plan: dict[str, Any]) -> int:
    down_payment = int(plan.get("down_payment") or 0)
    if down_payment <= 0:
        return 6

    available = int(plan.get("available_cash") or 0)
    readiness_ratio = min(available / down_payment if down_payment else 1, 1)
    saving = effective_monthly_capacity(profile)
    target_months = max(int(profile.get("target_months", 1)), 1)
    contract_date = _parse_date(notice.get("contract_date"))
    contract_days = (contract_date - date.today()).days if contract_date else 0
    shortfall = int(plan.get("shortfall") or 0)
    monthly_target = int(plan.get("monthly_target") or 0)

    score = 0
    score += round(readiness_ratio * 10)
    score += 5 if shortfall <= SHORTFALL_LOW_WON else 3 if shortfall <= SHORTFALL_MID_WON else 1
    if monthly_target <= 0:
        score += 4
    elif saving <= 0:
        score += 0
    else:
        score += 7 if monthly_target <= saving else 4 if monthly_target <= saving * 1.5 else 1
    score += 3 if target_months >= 12 and contract_days >= 30 else 1
    return max(0, min(score, 25))


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None
