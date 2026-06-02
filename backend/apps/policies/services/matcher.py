from __future__ import annotations

from typing import Any

from apps.fixture_store import policies
from apps.rules.matching import policy_match_score


def match_policies(profile: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for policy in policies():
        score, source_priority = policy_match_score(policy, profile)
        next_policy = policy.copy()
        next_policy["match_score"] = score
        next_policy["reasons"] = list(policy.get("reasons", [])) or [
            "나이, 소득, 선호 지역 조건을 기준으로 정렬했습니다."
        ]
        ranked.append((score, source_priority, next_policy))

    return [
        policy
        for score, _source_priority, policy in sorted(ranked, key=lambda item: (item[0], item[1]), reverse=True)[:limit]
        if score > 0
    ]
