from __future__ import annotations

from datetime import date
from typing import Any


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
    return min(score, 35)
