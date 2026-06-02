from __future__ import annotations

from datetime import date, datetime
from typing import Any


SCORE_WEIGHTS = {
    "eligibility": 35,
    "funding": 25,
    "location": 30,
    "schedule": 10,
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
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)
    down_payment = int(option.get("down_payment") or 0)
    middle_payment = int(option.get("middle_payment") or 0)

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
    elif down_payment:
        score += 8
    else:
        score += 5

    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        score += 10
    elif monthly_need:
        score += 4
    else:
        score += 5

    return min(score, 100)


def option_fit_reasons(option: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    area = float(option.get("exclusive_area_m2") or 0)
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(option.get("base_price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    down_payment = int(option.get("down_payment") or 0)
    middle_payment = int(option.get("middle_payment") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)

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
    elif down_payment:
        reasons.append("계약금 준비액이 부족할 수 있습니다.")

    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        reasons.append("중도금 예상 부담이 월 저축 여력 안에 있습니다.")
    elif monthly_need:
        reasons.append("중도금 납부 계획은 추가 자금 점검이 필요합니다.")

    return reasons[:4]

