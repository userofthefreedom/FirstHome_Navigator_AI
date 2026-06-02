from __future__ import annotations

from datetime import date, datetime
from typing import Any


SCORE_WEIGHTS = {
    "eligibility": 35,
    "funding": 25,
    "location": 30,
    "schedule": 10,
}

SCHEDULE_BURDEN_TYPES = {"middle_payment", "installment_payment"}
DOWN_PAYMENT_TYPES = {"down_payment"}
REGION_ALIASES = {
    "서울": ("서울", "서울특별시"),
    "부산": ("부산", "부산광역시"),
    "대구": ("대구", "대구광역시"),
    "인천": ("인천", "인천광역시"),
    "광주": ("광주", "광주광역시"),
    "대전": ("대전", "대전광역시"),
    "울산": ("울산", "울산광역시"),
    "세종": ("세종", "세종특별자치시"),
    "경기": ("경기", "경기도", "경기 남부", "경기 북부"),
    "경기 남부": ("경기 남부", "경기남부", "경기도"),
    "경기 북부": ("경기 북부", "경기북부", "경기도"),
    "강원": ("강원", "강원도", "강원특별자치도"),
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
    "제주": ("제주", "제주도", "제주특별자치도"),
}


def eligibility_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    age = date.today().year - int(profile.get("birth_year", date.today().year))
    tags = set(notice.get("tags", []))
    special_conditions = set(profile.get("special_conditions", []))
    income = int(profile.get("annual_income", 0))
    asset = int(profile.get("asset", 0))

    score = 0
    score += 8 if profile.get("is_homeless") else 0
    score += 7 if int(profile.get("subscription_months", 0)) >= int(notice.get("required_subscription_months", 24)) else 3
    score += 6 if int(notice.get("age_min", 19)) <= age <= int(notice.get("age_max", 150)) else 2
    score += 6 if income <= int(notice.get("max_income", 10**12)) else 0
    score += 4 if asset <= int(notice.get("max_asset", 10**12)) else 0

    special_match = ("first_home" in special_conditions and "생애최초" in tags) or (
        "youth" in special_conditions and "청년" in tags
    )
    score += 4 if special_match else 1
    return min(score, SCORE_WEIGHTS["eligibility"])


def location_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    preferred_regions = [str(region or "").strip() for region in profile.get("preferred_regions", [])]
    preferred_supply_types = [str(supply_type or "").strip() for supply_type in profile.get("preferred_supply_types", [])]
    notice_region = str(notice.get("region") or "")
    notice_district = str(notice.get("district") or "")

    score = 0
    score += 24 if any(
        _region_matches(notice_region, region) or _region_matches(notice_district, region)
        for region in preferred_regions
    ) else 0
    score += 6 if any(_supply_type_matches(notice, supply_type) for supply_type in preferred_supply_types) else 0
    return min(score, SCORE_WEIGHTS["location"])


def _region_matches(target: str, preferred_region: str) -> bool:
    target_key = _normalize_key(target)
    if not target_key:
        return False
    aliases = REGION_ALIASES.get(preferred_region, (preferred_region,))
    return any(_normalize_key(alias) in target_key for alias in aliases if alias)


def _supply_type_matches(notice: dict[str, Any], preferred_supply_type: str) -> bool:
    preferred_key = _normalize_key(preferred_supply_type)
    if not preferred_key:
        return False
    target_key = _normalize_key(f"{notice.get('supply_type', '')} {notice.get('housing_type', '')}")
    return preferred_key in target_key


def _normalize_key(value: Any) -> str:
    return "".join(str(value or "").split())


def schedule_score(notice: dict[str, Any]) -> int:
    today = date.today()
    days_left = (_parse_date(notice["application_deadline"]) - today).days
    contract_days = (_parse_date(notice["contract_date"]) - today).days

    score = 0
    score += 3 if days_left >= 7 else 1 if days_left >= 0 else 0
    score += 5 if contract_days >= 30 else 2 if contract_days >= 0 else 0
    score += 2 if str(notice.get("move_in", "")) >= "2027-01" else 1
    return min(score, SCORE_WEIGHTS["schedule"])


def score_max() -> int:
    return sum(SCORE_WEIGHTS.values())


def option_type_priority(option_type: str) -> int:
    if option_type == "general_supply":
        return 4
    if option_type == "basic":
        return 3
    if option_type == "pre_subscription":
        return 2
    if option_type == "minus":
        return 1
    return 0


def option_fit_score(option: dict[str, Any], profile: dict[str, Any]) -> int:
    score = 0
    area = float(option.get("exclusive_area_m2") or 0)
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(option.get("base_price") or option.get("price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    insights = option_funding_insights(option, profile)
    down_payment = int(insights["down_payment"])
    monthly_need = int(insights["monthly_schedule_need"])
    monthly_capacity = int(insights["monthly_capacity"])
    move_in_cash_gap = int(insights["move_in_cash_gap"])

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        score += 35
    elif area and ((min_area and area >= min_area * 0.9) or (max_area and area <= max_area * 1.1)):
        score += 15

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        score += 35
    elif price and ((min_price and price >= min_price * 0.9) or (max_price and price <= max_price * 1.1)):
        score += 15
    elif not price:
        score += 10

    if down_payment and max_down_payment and down_payment <= max_down_payment:
        score += 20
    elif down_payment and int(insights["down_payment_shortfall"]) <= monthly_capacity * max(int(profile.get("target_months", 1) or 1), 1):
        score += 14
    elif down_payment:
        score += 8
    else:
        score += 5

    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        score += 10
    elif monthly_need and monthly_capacity and monthly_need <= monthly_capacity * 1.5:
        score += 6
    elif monthly_need:
        score += 4
    else:
        score += 5

    if move_in_cash_gap == 0 and int(insights["due_before_move_in"]) > 0:
        score += 4
    elif move_in_cash_gap and monthly_capacity and move_in_cash_gap <= monthly_capacity * 6:
        score += 2
    elif move_in_cash_gap:
        score -= 6

    if int(insights["loan_amount"]) > 0:
        score -= 4 if int(insights["loan_monthly_hint"]) > monthly_capacity and monthly_capacity else 1
    if int(insights["due_before_move_in"]) > 0 and price and int(insights["due_before_move_in"]) <= price:
        score += 2

    return min(score, 100)


def option_fit_reasons(option: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    area = float(option.get("exclusive_area_m2") or 0)
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(option.get("base_price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    insights = option_funding_insights(option, profile)
    down_payment = int(insights["down_payment"])
    max_down_payment = int(insights["max_down_payment"])
    monthly_capacity = int(insights["monthly_capacity"])
    monthly_need = int(insights["monthly_schedule_need"])
    move_in_cash_gap = int(insights["move_in_cash_gap"])

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        reasons.append("희망 면적 범위에 들어옵니다.")
    elif area:
        reasons.append("희망 면적과 가까운 대안입니다.")

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        reasons.append("희망 분양가 범위에 들어옵니다.")
    elif price:
        reasons.append("희망 분양가와 차이가 있어 자금 여유를 확인해야 합니다.")
    else:
        reasons.append("분양가 근거가 부족해 공식 공고문 확인이 필요합니다.")

    if down_payment and max_down_payment and down_payment <= max_down_payment:
        reasons.append("계약금이 설정한 준비 가능 금액 안에 있습니다.")
    elif down_payment and int(insights["down_payment_shortfall"]) > 0:
        reasons.append(
            f"계약금 부족액 {int(insights['down_payment_shortfall']):,}원을 월 {int(insights['down_payment_monthly_target']):,}원씩 준비해야 합니다."
        )
    elif down_payment:
        reasons.append("계약금 준비액이 부족할 수 있습니다.")

    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        reasons.append("중도금과 할부금 일정 부담이 월 준비 여력 안에 있습니다.")
    elif monthly_need:
        reasons.append("중도금과 할부금 일정이 촘촘해 추가 자금 계획이 필요합니다.")

    if move_in_cash_gap > 0:
        reasons.append(f"입주 전 납부 총액 기준 약 {move_in_cash_gap:,}원의 추가 준비 여지를 확인해야 합니다.")

    if int(option.get("loan_amount") or 0) > 0:
        reasons.append(
            f"융자금 {int(insights['loan_amount']):,}원은 잔금 이후 상환 계획을 별도로 확인해야 합니다."
        )

    return reasons[:4]


def option_funding_insights(option: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    schedules = _payment_schedules(option)
    down_payment = _down_payment_amount(option)
    middle_payment = sum(
        int(schedule.get("amount") or 0)
        for schedule in schedules
        if str(schedule.get("payment_type") or "") == "middle_payment"
    ) or int(option.get("middle_payment") or 0)
    installment_payment = sum(
        int(schedule.get("amount") or 0)
        for schedule in schedules
        if str(schedule.get("payment_type") or "") == "installment_payment"
    ) or int(option.get("installment_payment") or 0)
    final_payment = sum(
        int(schedule.get("amount") or 0)
        for schedule in schedules
        if str(schedule.get("payment_type") or "") in {"final_payment", "move_in_balance"}
    ) or int(option.get("final_payment") or 0)
    loan_amount = int(option.get("loan_amount") or 0)
    max_down_payment = int(profile.get("max_down_payment") or profile.get("asset") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)
    target_months = max(int(profile.get("target_months") or 1), 1)
    down_payment_shortfall = max(0, down_payment - max_down_payment)
    down_payment_monthly_target = _ceil_divide(down_payment_shortfall, target_months)
    schedule_burden_schedules = [
        schedule
        for schedule in schedules
        if str(schedule.get("payment_type") or "") in SCHEDULE_BURDEN_TYPES and int(schedule.get("amount") or 0) > 0
    ]
    schedule_span_months = _schedule_span_months(schedule_burden_schedules) if schedule_burden_schedules else target_months
    monthly_schedule_need = _monthly_schedule_need(option)
    loan_monthly_hint = _ceil_divide(loan_amount, 60) if loan_amount else 0
    due_before_move_in = down_payment + middle_payment + installment_payment + final_payment
    available_before_move_in = max_down_payment + monthly_capacity * max(schedule_span_months, target_months)
    move_in_cash_gap = max(0, due_before_move_in - available_before_move_in)
    return {
        "down_payment": down_payment,
        "middle_payment": middle_payment,
        "installment_payment": installment_payment,
        "final_payment": final_payment,
        "loan_amount": loan_amount,
        "due_before_move_in": due_before_move_in,
        "max_down_payment": max_down_payment,
        "monthly_capacity": monthly_capacity,
        "target_months": target_months,
        "down_payment_shortfall": down_payment_shortfall,
        "down_payment_monthly_target": down_payment_monthly_target,
        "schedule_span_months": schedule_span_months,
        "monthly_schedule_need": monthly_schedule_need,
        "loan_monthly_hint": loan_monthly_hint,
        "available_before_move_in": available_before_move_in,
        "move_in_cash_gap": move_in_cash_gap,
        "can_cover_down_payment": down_payment > 0 and down_payment_shortfall == 0,
        "can_prepare_shortfall": down_payment_shortfall == 0 or (
            monthly_capacity > 0 and down_payment_monthly_target <= monthly_capacity
        ),
        "can_handle_schedule": monthly_schedule_need == 0 or (
            monthly_capacity > 0 and monthly_schedule_need <= monthly_capacity
        ),
        "has_post_balance_loan": loan_amount > 0,
        "can_handle_post_balance_loan": loan_amount == 0 or monthly_capacity == 0 or loan_monthly_hint <= monthly_capacity,
    }


def _down_payment_amount(option: dict[str, Any]) -> int:
    schedules = _payment_schedules(option)
    scheduled_amount = sum(
        int(schedule.get("amount") or 0)
        for schedule in schedules
        if str(schedule.get("payment_type") or "") in DOWN_PAYMENT_TYPES
    )
    return scheduled_amount or int(option.get("down_payment") or 0)


def _monthly_schedule_need(option: dict[str, Any]) -> int:
    schedules = [
        schedule
        for schedule in _payment_schedules(option)
        if str(schedule.get("payment_type") or "") in SCHEDULE_BURDEN_TYPES and int(schedule.get("amount") or 0) > 0
    ]
    if not schedules:
        middle_payment = int(option.get("middle_payment") or 0)
        installment_payment = int(option.get("installment_payment") or 0)
        return (middle_payment + installment_payment) // 24 if middle_payment or installment_payment else 0

    total = sum(int(schedule.get("amount") or 0) for schedule in schedules)
    months = _schedule_span_months(schedules)
    return total // months


def _payment_schedules(option: dict[str, Any]) -> list[dict[str, Any]]:
    schedules = option.get("payment_schedules") or []
    return [schedule for schedule in schedules if isinstance(schedule, dict)]


def _schedule_span_months(schedules: list[dict[str, Any]]) -> int:
    due_dates = [
        parsed
        for parsed in (_parse_optional_date(schedule.get("due_date")) for schedule in schedules)
        if parsed is not None
    ]
    if len(due_dates) < 2:
        return max(1, len(schedules))
    first = min(due_dates)
    last = max(due_dates)
    return max(1, (last.year - first.year) * 12 + last.month - first.month + 1)


def _ceil_divide(amount: int, divisor: int) -> int:
    if amount <= 0:
        return 0
    return (amount + max(divisor, 1) - 1) // max(divisor, 1)


def _parse_date(value: Any) -> date:
    parsed = _parse_optional_date(value)
    if parsed is None:
        return date.today()
    return parsed


def _parse_optional_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None
