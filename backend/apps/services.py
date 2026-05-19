from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "firsthome_mvp.json"


@lru_cache(maxsize=1)
def load_fixture() -> dict[str, Any]:
    with Path(FIXTURE_PATH).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def default_profile() -> dict[str, Any]:
    return load_fixture()["profile"].copy()


def notices() -> list[dict[str, Any]]:
    return [notice.copy() for notice in load_fixture()["notices"]]


def products() -> list[dict[str, Any]]:
    return [product.copy() for product in load_fixture()["products"]]


def policies() -> list[dict[str, Any]]:
    return [policy.copy() for policy in load_fixture()["policies"]]


def find_notice(notice_id: int) -> dict[str, Any] | None:
    return next((notice for notice in notices() if notice["id"] == notice_id), None)


def calculate_score(notice: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or default_profile()
    age = date.today().year - int(profile["birth_year"])
    special_conditions = set(profile.get("special_conditions", []))
    preferred_regions = set(profile.get("preferred_regions", []))
    preferred_supply_types = set(profile.get("preferred_supply_types", []))
    tags = set(notice.get("tags", []))

    eligibility = 0
    eligibility += 8 if profile.get("is_homeless") else 0
    eligibility += 7 if int(profile.get("subscription_months", 0)) >= 24 else 4
    eligibility += 6 if 19 <= age <= 34 else 2
    eligibility += 10 if int(profile.get("annual_income", 0)) <= 50000000 else 5
    special_match = ("first_home" in special_conditions and "생애최초" in tags) or (
        "youth" in special_conditions and "청년" in tags
    )
    eligibility += 4 if special_match else 0

    down_payment = round(int(notice["price"]) * float(notice.get("contract_rate", 0.1)))
    available_cash = max(0, int(profile.get("asset", 0)) - int(profile.get("debt", 0)))
    shortfall = max(0, down_payment - available_cash)
    target_months = max(int(profile.get("target_months", 1)), 1)
    monthly_target = -(-shortfall // target_months)
    saving = int(profile.get("monthly_saving", 0))
    readiness_ratio = min(available_cash / down_payment if down_payment else 1, 1)

    funding = 0
    funding += round(readiness_ratio * 10)
    funding += 5 if shortfall <= 30000000 else 3 if shortfall <= 50000000 else 1
    funding += 7 if monthly_target <= saving else 4 if monthly_target <= saving * 1.5 else 1
    funding += 3 if target_months >= 12 else 1

    location = 0
    location += 9 if notice["region"] in preferred_regions else 3
    location += 3 if any(region in notice["district"] for region in preferred_regions) else 0
    location += 3 if notice["supply_type"] in preferred_supply_types or notice["housing_type"] in preferred_supply_types else 0

    days_left = (datetime.fromisoformat(notice["application_deadline"]).date() - date.today()).days
    contract_days = (datetime.fromisoformat(notice["contract_date"]).date() - date.today()).days
    schedule = 0
    schedule += 3 if days_left >= 7 else 1
    schedule += 5 if contract_days >= 30 else 2
    schedule += 2 if str(notice.get("move_in", "")) >= "2027-01" else 1

    policy_link = 0
    policy_link += 6 if products() else 0
    policy_link += 6 if policies() else 0
    policy_link += 3 if notice.get("source_url") else 1

    detail = {
        "eligibility": min(eligibility, 35),
        "funding": min(funding, 25),
        "location": min(location, 15),
        "schedule": min(schedule, 10),
        "policy_link": min(policy_link, 15),
    }

    reasons = [
        f"{notice['region']} 희망 지역과 {notice['supply_type']} 선호 조건을 반영했습니다.",
        f"계약금 예상액은 {down_payment:,}원이고 현재 준비 가능 현금은 {available_cash:,}원입니다.",
        "청년/생애최초 조건은 공식 공고문에서 최종 확인해야 합니다.",
    ]

    return {
        "notice_id": notice["id"],
        "title": notice["title"],
        "provider": notice["provider"],
        "region": notice["region"],
        "district": notice["district"],
        "supply_type": notice["supply_type"],
        "housing_type": notice["housing_type"],
        "area": notice["area"],
        "price": notice["price"],
        "application_deadline": notice["application_deadline"],
        "winner_date": notice["winner_date"],
        "contract_date": notice["contract_date"],
        "move_in": notice["move_in"],
        "competition": notice["competition"],
        "source_url": notice.get("source_url", ""),
        "total_score": sum(detail.values()),
        "score_detail": detail,
        "reasons": reasons,
    }


def funding_plan(notice_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    if notice is None:
        return None

    price = int(notice["price"])
    down_payment = round(price * float(notice.get("contract_rate", 0.1)))
    available_cash = max(0, int(profile.get("asset", 0)) - int(profile.get("debt", 0)))
    shortfall = max(0, down_payment - available_cash)
    months = max(int(profile.get("target_months", 1)), 1)

    return {
        "notice_id": notice_id,
        "notice_title": notice["title"],
        "price": price,
        "down_payment": down_payment,
        "available_cash": available_cash,
        "shortfall": shortfall,
        "months_until_contract": months,
        "monthly_target": -(-shortfall // months),
        "timeline": [
            {"label": "청약 접수 마감", "date": notice["application_deadline"], "amount": 0},
            {"label": "당첨자 발표", "date": notice["winner_date"], "amount": 0},
            {"label": "계약금 납부", "date": notice["contract_date"], "amount": down_payment},
            {"label": "중도금 계획 확인", "date": notice["contract_date"], "amount": round(price * 0.6)},
            {"label": "잔금 계획 확인", "date": notice["move_in"], "amount": round(price * 0.3)},
        ],
    }


def coach_summary(notice_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile)
    if notice is None or plan is None:
        return None

    return {
        "source": "template_fallback",
        "summary": (
            f"{notice['title']}은(는) {notice['region']} 희망 지역과 첫 집 준비 조건에 잘 맞는 후보입니다. "
            f"계약금 기준 부족액은 {plan['shortfall']:,}원이므로 월 {plan['monthly_target']:,}원 수준의 준비 계획이 필요합니다."
        ),
        "todo_this_week": [
            "주민등록등본, 소득금액증명원, 청약통장 가입확인서 발급 가능 여부를 확인하세요.",
            f"{notice['provider']} 또는 공식 청약 사이트에서 청년/생애최초 세부 조건을 확인하세요.",
            "계약금으로 사용할 돈은 생활비 계좌와 분리해 관리하세요.",
        ],
        "official_checklist": [
            "무주택 및 세대 구성 기준",
            "소득, 자산, 청약통장 납입 인정 기준",
            "접수 마감일, 계약일, 분양가와 납부 일정",
        ],
        "warning": "이 결과는 공개 데이터와 fixture 기반 참고 정보입니다. 실제 신청 전 공식 공고문을 반드시 확인하세요.",
    }
