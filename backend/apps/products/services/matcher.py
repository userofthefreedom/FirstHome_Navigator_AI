from __future__ import annotations

from typing import Any

from apps.fixture_store import products
from apps.rules.matching import product_match_score


def match_products(profile: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for product in products():
        score = product_match_score(product, profile)
        next_product = product.copy()
        next_product["match_score"] = score
        next_product["reasons"] = list(product.get("reasons", [])) or [
            "목표 기간과 월 저축 가능액 기준으로 정렬했습니다."
        ]
        ranked.append((score, next_product))

    return [product for score, product in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit] if score > 0]
