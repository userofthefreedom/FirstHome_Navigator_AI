from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import current_notices, find_notice, notices
from apps.notices.services.map_locations import offset_location, resolve_notice_location
from apps.profiles.services import profile_from_request
from apps.recommendations.services.ranking import calculate_score
from apps.rules.cache_keys import cache_key, data_version, profile_hash
from apps.rules.cache_service import get_or_set_locked
from apps.rules.regions import canonical_region


@api_view(["GET"])
def notice_list(request):
    include_excluded = request.query_params.get("include_excluded") in {"1", "true", "yes"}
    active_only = request.query_params.get("active") in {"1", "true", "yes"}
    source = current_notices if active_only else notices
    return Response(
        source(
            include_excluded=include_excluded,
            region=request.query_params.get("region") or None,
            ownership_type=request.query_params.get("ownership_type") or None,
        )
    )


@api_view(["GET"])
def notice_detail(request, notice_id):
    notice = find_notice(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(notice)


@api_view(["GET"])
def notice_map(request):
    include_excluded = request.query_params.get("include_excluded") in {"1", "true", "yes"}
    ownership_type = request.query_params.get("ownership_type") or None
    profile = profile_from_request(request)
    key = cache_key("notice-map", data_version(), profile_hash(profile), include_excluded, ownership_type or "")
    return Response(
        get_or_set_locked(
            key,
            lambda: _notice_map_payload(profile, include_excluded=include_excluded, ownership_type=ownership_type),
            timeout=60,
        )
    )


def _notice_map_payload(profile, *, include_excluded: bool, ownership_type: str | None):
    raw_notices = [
        notice
        for notice in current_notices(include_excluded=include_excluded, ownership_type=ownership_type)
        if include_excluded or notice.get("is_service_target")
    ]
    marker_counts: dict[tuple[float, float], int] = {}
    items = []
    for notice in raw_notices:
        location = resolve_notice_location(notice)
        map_region = _map_region(notice)
        key = (round(location["lat"], 4), round(location["lng"], 4))
        index = marker_counts.get(key, 0)
        marker_counts[key] = index + 1
        scored = calculate_score(notice, profile)
        representative_price = int(notice.get("price") or 0) or _representative_option_price(scored)
        items.append(
            {
                "notice_id": notice["id"],
                "title": notice["title"],
                "provider": notice["provider"],
                "region": notice["region"],
                "map_region": map_region,
                "district": notice["district"],
                "supply_type": notice["supply_type"],
                "housing_type": notice["housing_type"],
                "area": notice.get("area", ""),
                "price": representative_price,
                "application_deadline": notice.get("application_deadline", ""),
                "data_source": notice.get("data_source", ""),
                "source_url": notice.get("source_url", ""),
                "official_document_status": notice.get("official_document_status", "not_requested"),
                "analysis_summary": notice.get("analysis_summary", {}),
                "document_count": notice.get("document_count", 0),
                "unit_option_count": notice.get("unit_option_count", 0),
                "total_score": scored["total_score"],
                "score_max": scored["score_max"],
                "score_detail": scored["score_detail"],
                "best_option": scored.get("best_option"),
                "top_options": scored.get("top_options", []),
                "location": offset_location(location, index),
            }
        )
    items.sort(key=lambda item: (item["total_score"], item["application_deadline"]), reverse=True)
    return {"items": items, "count": len(items)}


def _representative_option_price(scored: dict) -> int:
    best_option = scored.get("best_option") or {}
    if int(best_option.get("base_price") or 0) > 0:
        return int(best_option.get("base_price") or 0)
    for option in scored.get("top_options", []):
        price = int(option.get("base_price") or 0)
        if price > 0:
            return price
    return 0


def _map_region(notice: dict) -> str:
    return canonical_region(notice.get("region"), notice.get("district"), notice.get("title"))
