from __future__ import annotations

from typing import Any

from apps.fixture_store import default_profile, notices
from apps.recommendations.services.scoring import score_detail, score_reasons


def calculate_score(notice: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or default_profile()
    detail = score_detail(notice, profile)
    return {
        "notice_id": notice["id"],
        "source_id": notice.get("source_id", ""),
        "data_source": notice.get("data_source", "fixture"),
        "is_price_confirmed": notice.get("is_price_confirmed", int(notice.get("price") or 0) > 0),
        "source_meta": notice.get("source_meta", {}),
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
        "reasons": score_reasons(notice, profile),
    }


def ranked_recommendations(profile: dict[str, Any] | None = None, limit: int = 3) -> list[dict[str, Any]]:
    profile = profile or default_profile()
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in notices()],
        key=lambda item: item["total_score"],
        reverse=True,
    )
    return recommendations[:limit]
