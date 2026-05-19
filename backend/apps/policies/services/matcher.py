from __future__ import annotations

from datetime import date
from typing import Any

from apps.fixture_store import policies


def match_policies(profile: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    age = date.today().year - int(profile.get("birth_year", date.today().year))
    income = int(profile.get("annual_income", 0))
    preferred_regions = set(profile.get("preferred_regions", []))
    is_homeless = bool(profile.get("is_homeless"))

    ranked: list[tuple[int, dict[str, Any]]] = []
    for policy in policies():
        score = 0
        if int(policy.get("age_min", 0)) <= age <= int(policy.get("age_max", 150)):
            score += 4
        if income <= int(policy.get("max_income", 10**12)):
            score += 3
        policy_regions = set(policy.get("regions", []))
        if "전국" in policy_regions or preferred_regions & policy_regions:
            score += 3
        if not policy.get("requires_homeless") or is_homeless:
            score += 2
        if policy.get("policy_category") in {"월세", "전세", "주거지원", "상담"}:
            score += 1
        if policy.get("source_url"):
            score += 1

        next_policy = policy.copy()
        next_policy["match_score"] = score
        next_policy["reasons"] = list(policy.get("reasons", [])) or [
            "나이, 소득, 희망 지역 조건을 기준으로 정렬했습니다."
        ]
        ranked.append((score, next_policy))

    return [policy for score, policy in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit] if score > 0]
