from __future__ import annotations

from typing import Any

from apps.fixture_store import products
from apps.products.models import FinancialProduct
from apps.rules.matching import product_match_score


def match_products(profile: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for product in _candidate_products():
        score = product_match_score(product, profile)
        next_product = product.copy()
        next_product["match_score"] = score
        next_product["reasons"] = list(product.get("reasons", [])) or [
            "목표 기간과 월 저축 가능액 기준으로 정렬했습니다."
        ]
        ranked.append((score, next_product))

    return [product for score, product in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit] if score > 0]


def _candidate_products() -> list[dict[str, Any]]:
    try:
        queryset = FinancialProduct.objects.prefetch_related("options").order_by("provider", "name")
        if queryset.exists():
            return [_serialize_product(product) for product in queryset]
    except Exception:
        pass
    return products()


def _serialize_product(product: FinancialProduct) -> dict[str, Any]:
    options = list(product.options.all())
    best_option = max(options, key=lambda item: (item.intr_rate2, item.intr_rate, item.save_trm), default=None)
    best_rate = max(float(best_option.intr_rate2 or best_option.intr_rate or 0), 0) if best_option else 0
    return {
        "id": product.id,
        "name": product.name,
        "provider": product.provider,
        "category": product.category,
        "rate": product.rate or (f"최고 연 {best_rate:.2f}%" if best_rate else ""),
        "limit": "한도 없음" if not product.monthly_limit else f"월 {round(product.monthly_limit / 10000):,}만원",
        "period": "상시" if not product.term_months else f"{product.term_months}개월",
        "term_months": product.term_months,
        "monthly_limit": product.monthly_limit,
        "option_count": len(options),
        "protection_status": product.protection_status,
        "source_url": product.source_url,
        "reasons": product.reasons or ["자금 로드맵 준비액과 기간을 기준으로 비교할 수 있는 예적금 상품입니다."],
        "best_option": {
            "id": best_option.id,
            "save_trm": best_option.save_trm,
            "intr_rate": best_option.intr_rate,
            "intr_rate2": best_option.intr_rate2,
            "intr_rate_type_nm": best_option.intr_rate_type_nm,
        } if best_option else None,
    }
