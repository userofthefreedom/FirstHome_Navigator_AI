from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import current_notices, find_notice, notices
from apps.notices.services.map_locations import offset_location, resolve_notice_location
from apps.profiles.services import profile_from_request
from apps.recommendations.services.ranking import calculate_score


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
                "price": notice.get("price", 0),
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
    return Response({"items": items, "count": len(items)})


def _map_region(notice: dict) -> str:
    region = str(notice.get("region") or "").strip()
    text = f"{region} {notice.get('district', '')} {notice.get('title', '')}".replace(" ", "")
    if "경기북부" in text:
        return "경기 북부"
    if "경기남부" in text:
        return "경기 남부"
    if "경기" in text or "경기도" in text:
        northern = ("고양", "남양주", "파주", "의정부", "양주", "구리", "포천", "동두천", "가평", "연천")
        return "경기 북부" if any(name in text for name in northern) else "경기 남부"
    aliases = (
        ("서울", ("서울", "서울특별시")),
        ("부산", ("부산", "부산광역시")),
        ("대구", ("대구", "대구광역시")),
        ("인천", ("인천", "인천광역시")),
        ("광주", ("광주", "광주광역시")),
        ("대전", ("대전", "대전광역시")),
        ("울산", ("울산", "울산광역시")),
        ("세종", ("세종", "세종특별자치시")),
        ("강원", ("강원", "강원도", "강원특별자치도")),
        ("충북", ("충북", "충청북도")),
        ("충남", ("충남", "충청남도")),
        ("전북", ("전북", "전라북도", "전북특별자치도")),
        ("전남", ("전남", "전라남도")),
        ("경북", ("경북", "경상북도")),
        ("경남", ("경남", "경상남도")),
        ("제주", ("제주", "제주도", "제주특별자치도")),
    )
    normalized_region = region.replace(" ", "")
    for label, names in aliases:
        if any(name.replace(" ", "") in normalized_region for name in names):
            return label
    return region or "전국"
