from __future__ import annotations

import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

DEFAULT_ORIGIN = {"lat": 37.5012743, "lng": 127.039585, "name": "멀티캠퍼스 역삼"}


@api_view(["GET"])
def search_places_view(request):
    place_type = request.query_params.get("type", "bank")
    query = request.query_params.get("query", "").strip()
    lat = request.query_params.get("lat") or DEFAULT_ORIGIN["lat"]
    lng = request.query_params.get("lng") or DEFAULT_ORIGIN["lng"]
    radius = request.query_params.get("radius", "2000")
    api_key = settings.EXTERNAL_API_KEYS.get("KAKAO_REST_API_KEY", "")
    if not api_key:
        return Response({"items": _fallback_places(place_type), "fallback": True})

    params = {"x": lng, "y": lat, "radius": radius, "size": 15, "sort": "distance"}
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    if place_type == "bank" and not query:
        params["category_group_code"] = "BK9"
    else:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        params["query"] = query or ("은행" if place_type == "bank" else "부동산 공인중개사")

    try:
        response = requests.get(url, params=params, headers={"Authorization": f"KakaoAK {api_key}"}, timeout=8)
        response.raise_for_status()
        items = [_serialize_place(row, place_type) for row in response.json().get("documents", [])]
    except Exception:
        items = []
    return Response({"items": items or _fallback_places(place_type), "fallback": not bool(items)})


@api_view(["GET"])
def route_view(request):
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    if not lat or not lng:
        return Response({"detail": "lat and lng are required"}, status=400)
    return Response(
        {
            "origin": DEFAULT_ORIGIN,
            "destination": {"lat": float(lat), "lng": float(lng)},
            "direction_url": _direction_url(lat, lng),
            "polyline": [],
            "message": "Kakao Mobility 승인 전에는 Kakao Map 길찾기 URL로 안내합니다.",
        }
    )


def _serialize_place(row: dict, place_type: str) -> dict:
    lat = float(row.get("y") or 0)
    lng = float(row.get("x") or 0)
    return {
        "id": row.get("id", ""),
        "name": row.get("place_name", ""),
        "category": place_type,
        "address": row.get("address_name", ""),
        "road_address": row.get("road_address_name", ""),
        "phone": row.get("phone", ""),
        "distance": int(row.get("distance") or 0),
        "lat": lat,
        "lng": lng,
        "place_url": row.get("place_url", ""),
        "direction_url": _direction_url(lat, lng),
    }


def _direction_url(lat, lng) -> str:
    return f"https://map.kakao.com/link/to/목적지,{lat},{lng}/from/{DEFAULT_ORIGIN['name']},{DEFAULT_ORIGIN['lat']},{DEFAULT_ORIGIN['lng']}"


def _fallback_places(place_type: str) -> list[dict]:
    base = [
        ("국민은행 역삼동점", 37.5007, 127.0369, "서울 강남구 테헤란로"),
        ("신한은행 역삼역금융센터", 37.5001, 127.0397, "서울 강남구 논현로"),
        ("우리은행 강남역지점", 37.4986, 127.0283, "서울 강남구 강남대로"),
    ] if place_type == "bank" else [
        ("역삼공인중개사사무소", 37.5019, 127.0382, "서울 강남구 역삼동"),
        ("테헤란부동산", 37.5031, 127.0415, "서울 강남구 테헤란로"),
    ]
    return [
        {
            "id": f"fixture-{index}",
            "name": name,
            "category": place_type,
            "address": address,
            "road_address": address,
            "phone": "",
            "distance": 200 + index * 150,
            "lat": lat,
            "lng": lng,
            "place_url": f"https://map.kakao.com/link/search/{name}",
            "direction_url": _direction_url(lat, lng),
        }
        for index, (name, lat, lng, address) in enumerate(base, 1)
    ]
