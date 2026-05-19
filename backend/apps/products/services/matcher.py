from __future__ import annotations

from typing import Any

from apps.fixture_store import products


def match_products(profile: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    target_months = int(profile.get("target_months", 0))
    monthly_saving = int(profile.get("monthly_saving", 0))

    ranked: list[tuple[int, dict[str, Any]]] = []
    for product in products():
        term_months = int(product.get("term_months", 0))
        monthly_limit = int(product.get("monthly_limit", 0))
        protected = bool(product.get("protection_status"))

        score = 0
        if term_months and abs(term_months - target_months) <= 6:
            score += 4
        elif term_months and term_months <= max(target_months, 1) + 12:
            score += 2
        if monthly_limit == 0 or monthly_limit >= monthly_saving:
            score += 3
        elif monthly_limit >= monthly_saving * 0.7:
            score += 2
        if product.get("category") in {"적금", "청약통장"}:
            score += 2
        if protected:
            score += 1
        if product.get("source_url"):
            score += 1

        next_product = product.copy()
        next_product["match_score"] = score
        next_product["reasons"] = list(product.get("reasons", [])) or [
            "목표 기간과 월 저축 가능액을 기준으로 정렬했습니다."
        ]
        ranked.append((score, next_product))

    return [product for score, product in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit] if score > 0]
