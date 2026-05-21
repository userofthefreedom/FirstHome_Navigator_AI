from __future__ import annotations

from typing import Any

from apps.fixture_store import default_profile, notices
from apps.recommendations.services.scoring import score_detail, score_reasons


def _area_m2(value: str) -> float:
    digits = "".join(char if char.isdigit() or char == "." else " " for char in str(value or ""))
    for token in digits.split():
        try:
            return float(token)
        except ValueError:
            continue
    return 0


def _option_fit_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    score = 0
    area = _area_m2(notice.get("area", ""))
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(notice.get("price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        score += 35
    elif not area or (min_area and area >= min_area * 0.9) or (max_area and area <= max_area * 1.1):
        score += 15

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        score += 35
    elif not price:
        score += 10
    elif (min_price and price >= min_price * 0.9) or (max_price and price <= max_price * 1.1):
        score += 15

    down_payment = round(price * float(notice.get("contract_rate", 0.1))) if price else 0
    if down_payment and max_down_payment and down_payment <= max_down_payment:
        score += 20
    elif down_payment:
        score += 8
    else:
        score += 5

    middle_payment = round(price * float(notice.get("middle_payment_rate", 0.6))) if price else 0
    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        score += 10
    elif monthly_need:
        score += 4
    else:
        score += 5

    return min(score, 100)


def calculate_score(notice: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or default_profile()
    detail = score_detail(notice, profile)
    return {
        "notice_id": notice["id"],
        "source_id": notice.get("source_id", ""),
        "data_source": notice.get("data_source", "fixture"),
        "is_price_confirmed": notice.get("is_price_confirmed", int(notice.get("price") or 0) > 0),
        "source_meta": notice.get("source_meta", {}),
        "ownership_type": notice.get("ownership_type", "unknown"),
        "is_service_target": notice.get("is_service_target", False),
        "exclude_reason": notice.get("exclude_reason", ""),
        "official_document_status": notice.get("official_document_status", "not_requested"),
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
        "option_fit_score": _option_fit_score(notice, profile),
        "score_detail": detail,
        "reasons": score_reasons(notice, profile),
    }


def ranked_recommendations(profile: dict[str, Any] | None = None, limit: int = 3) -> list[dict[str, Any]]:
    profile = profile or default_profile()
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in notices()],
        key=lambda item: (item["option_fit_score"], item["total_score"]),
        reverse=True,
    )
    return recommendations[:limit]
