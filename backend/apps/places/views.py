from __future__ import annotations

from urllib.parse import quote

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import COMMON_ERROR_RESPONSES, PLACES_SEARCH_RESPONSE, ROUTE_RESPONSE, TAGS

DEFAULT_ORIGIN = {"lat": 37.5012743, "lng": 127.039585, "name": "멀티캠퍼스 역삼"}


@extend_schema(
    tags=[TAGS["places"]],
    summary="주변 은행/부동산 검색",
    description="Kakao Local API로 선택 지역 주변 은행 또는 부동산 중개업소를 검색합니다. API 키가 없으면 fallback 장소를 반환합니다.",
    parameters=[
        OpenApiParameter("type", str, OpenApiParameter.QUERY, description="bank 또는 estate"),
        OpenApiParameter("query", str, OpenApiParameter.QUERY, description="검색 중심으로 사용할 지역/주소/키워드"),
        OpenApiParameter("bank_brand", str, OpenApiParameter.QUERY, description="kb, shinhan, woori, hana 등 은행 브랜드 필터"),
        OpenApiParameter("lat", float, OpenApiParameter.QUERY, description="검색 중심 위도"),
        OpenApiParameter("lng", float, OpenApiParameter.QUERY, description="검색 중심 경도"),
        OpenApiParameter("radius", int, OpenApiParameter.QUERY, description="검색 반경 미터"),
    ],
    responses={200: PLACES_SEARCH_RESPONSE},
)
@api_view(["GET"])
def search_places_view(request):
    place_type = request.query_params.get("type", "bank")
    query = request.query_params.get("query", "").strip()
    bank_brand = request.query_params.get("bank_brand", "").strip()
    lat = request.query_params.get("lat") or DEFAULT_ORIGIN["lat"]
    lng = request.query_params.get("lng") or DEFAULT_ORIGIN["lng"]
    radius = request.query_params.get("radius", "2000")
    api_key = settings.EXTERNAL_API_KEYS.get("KAKAO_REST_API_KEY", "")
    if not api_key:
        return Response({"items": _fallback_places(place_type), "fallback": True})

    category_group_code = _category_group_code(place_type)
    search_center = _resolve_search_center(api_key, query, lat, lng) if query else {"lat": float(lat), "lng": float(lng)}
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    base_params = {
        "x": search_center["lng"],
        "y": search_center["lat"],
        "radius": radius,
        "category_group_code": category_group_code,
        "size": 15,
        "sort": "distance",
    }

    try:
        rows = _fetch_category_rows(url, base_params, api_key)
        if place_type == "bank":
            rows = [row for row in rows if _is_bank_branch(row, bank_brand)]
        items = [_serialize_place(row, place_type) for row in rows[:15]]
    except Exception:
        return Response({"items": _fallback_places(place_type), "fallback": True})
    if query:
        return Response({"items": items, "fallback": False, "center": search_center})
    return Response({"items": items or _fallback_places(place_type), "fallback": not bool(items)})


@extend_schema(
    tags=[TAGS["places"]],
    summary="지도 경로 조회",
    description="멀티캠퍼스 역삼 기준 선택 지점까지 Kakao REST API 키로 조회한 길찾기 polyline과 Kakao Map 길찾기 URL을 반환합니다.",
    parameters=[
        OpenApiParameter("lat", float, OpenApiParameter.QUERY, required=True, description="목적지 위도"),
        OpenApiParameter("lng", float, OpenApiParameter.QUERY, required=True, description="목적지 경도"),
    ],
    responses={200: ROUTE_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def route_view(request):
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    if not lat or not lng:
        return Response({"detail": "lat and lng are required"}, status=400)

    destination = {"lat": float(lat), "lng": float(lng)}
    api_key = settings.EXTERNAL_API_KEYS.get("KAKAO_REST_API_KEY", "")
    if not api_key:
        return Response(_fallback_route(destination, "Kakao REST API 키가 없어 지도 경로를 표시할 수 없습니다."))

    params = {
        "origin": f"{DEFAULT_ORIGIN['lng']},{DEFAULT_ORIGIN['lat']}",
        "destination": f"{destination['lng']},{destination['lat']}",
        "priority": "RECOMMEND",
        "summary": "false",
    }
    try:
        response = requests.get(
            "https://apis-navi.kakaomobility.com/v1/directions",
            params=params,
            headers={"Authorization": f"KakaoAK {api_key}", "Content-Type": "application/json"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        route = (payload.get("routes") or [{}])[0]
        if route.get("result_code") not in {None, 0}:
            result_message = route.get("result_msg") or "Kakao 길찾기 응답이 성공이 아닙니다."
            return Response(_fallback_route(destination, result_message))
        polyline = _extract_polyline(route)
        if len(polyline) < 2:
            return Response(_fallback_route(destination, "Kakao 길찾기 경로 좌표가 없어 지도 경로를 표시할 수 없습니다."))
        summary = route.get("summary") or {}
        return Response(
            {
                "origin": DEFAULT_ORIGIN,
                "destination": destination,
                "direction_url": _direction_url(destination["lat"], destination["lng"]),
                "polyline": polyline,
                "distance": summary.get("distance"),
                "duration": summary.get("duration"),
                "message": "Kakao 길찾기 경로를 지도에 표시했습니다.",
            }
        )
    except requests.HTTPError as exc:
        detail = _response_error_message(exc.response)
        return Response(_fallback_route(destination, f"Kakao 길찾기 호출 실패: {detail}"))
    except Exception:
        return Response(_fallback_route(destination, "Kakao 길찾기 경로 호출에 실패해 지도 경로를 표시할 수 없습니다."))


def _category_group_code(place_type: str) -> str:
    return "BK9" if place_type == "bank" else "AG2"


def _fetch_category_rows(url: str, params: dict, api_key: str) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 4):
        response = requests.get(
            url,
            params={**params, "page": page},
            headers={"Authorization": f"KakaoAK {api_key}"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        rows.extend(payload.get("documents", []))
        if payload.get("meta", {}).get("is_end", True):
            break
    return rows


BANK_BRANDS = {
    "kb": ("국민은행", "KB국민은행", "KB 은행", "KB"),
    "shinhan": ("신한은행", "신한"),
    "woori": ("우리은행", "우리"),
    "hana": ("하나은행", "KEB하나은행", "하나"),
    "nh": ("농협은행", "NH농협", "농협"),
    "ibk": ("기업은행", "IBK기업은행", "IBK"),
    "sc": ("SC제일은행", "제일은행", "SC"),
    "kdb": ("산업은행", "KDB산업은행", "KDB"),
    "suhyup": ("수협은행", "Sh수협", "수협"),
    "citi": ("씨티은행", "한국씨티은행", "씨티"),
    "kbank": ("케이뱅크", "케이뱅크은행"),
    "kakao": ("카카오뱅크", "카카오뱅크"),
    "toss": ("토스뱅크", "토스뱅크"),
    "saemaeul": ("새마을금고", "MG새마을금고"),
    "shinhyup": ("신협", "신용협동조합"),
}

BANK_BRANCH_HINTS = ("은행", "금융센터", "영업부", "지점", "출장소", "새마을금고", "신협", "신용협동조합")
BANK_EXCLUDE_HINTS = (
    "ATM",
    "365",
    "CD",
    "자동화",
    "무인",
    "점외",
    "편의점",
    "세븐일레븐",
    "GS25",
    "CU ",
    " CU",
    "이마트",
    "롯데마트",
    "현금인출",
    "현금지급",
)


def _is_bank_branch(row: dict, bank_brand: str = "") -> bool:
    name = row.get("place_name", "")
    category = row.get("category_name", "")
    haystack = f"{name} {category}"
    if any(token in haystack for token in BANK_EXCLUDE_HINTS):
        return False
    if bank_brand:
        brand_tokens = BANK_BRANDS.get(bank_brand, ())
        if brand_tokens and not any(token in haystack for token in brand_tokens):
            return False
    return any(token in haystack for token in BANK_BRANCH_HINTS)


def _resolve_search_center(api_key: str, query: str, fallback_lat, fallback_lng) -> dict[str, float]:
    headers = {"Authorization": f"KakaoAK {api_key}"}
    address_center = _search_address_center(headers, query)
    if address_center:
        return address_center
    for keyword in _center_keywords(query):
        keyword_center = _search_keyword_center(headers, keyword)
        if keyword_center:
            return keyword_center
    return {"lat": float(fallback_lat), "lng": float(fallback_lng)}


def _search_address_center(headers: dict[str, str], query: str) -> dict[str, float] | None:
    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        params={"query": query, "analyze_type": "similar", "size": 1},
        headers=headers,
        timeout=5,
    )
    response.raise_for_status()
    documents = response.json().get("documents", [])
    if not documents:
        return None
    row = documents[0]
    return {"lat": float(row["y"]), "lng": float(row["x"])}


def _search_keyword_center(headers: dict[str, str], query: str) -> dict[str, float] | None:
    response = requests.get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        params={"query": query, "size": 1, "sort": "accuracy"},
        headers=headers,
        timeout=5,
    )
    response.raise_for_status()
    documents = response.json().get("documents", [])
    if not documents:
        return None
    row = documents[0]
    return {"lat": float(row["y"]), "lng": float(row["x"])}


def _center_keywords(query: str) -> list[str]:
    normalized = query.strip()
    suffixes = ["시청", "구청", "군청", "역", "행정복지센터"]
    return [normalized, *[f"{normalized} {suffix}" for suffix in suffixes], *[f"{normalized}{suffix}" for suffix in suffixes]]


def _extract_polyline(route: dict) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for section in route.get("sections", []):
        for road in section.get("roads", []):
            vertices = road.get("vertexes") or []
            for index in range(0, len(vertices), 2):
                try:
                    lng = float(vertices[index])
                    lat = float(vertices[index + 1])
                except (IndexError, TypeError, ValueError):
                    continue
                points.append({"lat": lat, "lng": lng})
    return points


def _fallback_route(destination: dict, message: str) -> dict:
    return {
        "origin": DEFAULT_ORIGIN,
        "destination": destination,
        "direction_url": _direction_url(destination["lat"], destination["lng"]),
        "polyline": [],
        "message": message,
        "fallback": True,
    }


def _response_error_message(response) -> str:
    if response is None:
        return "응답 없음"
    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    return payload.get("msg") or payload.get("message") or payload.get("error") or f"HTTP {response.status_code}"


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
    destination = quote(f"목적지,{lat},{lng}")
    origin = quote(f"{DEFAULT_ORIGIN['name']},{DEFAULT_ORIGIN['lat']},{DEFAULT_ORIGIN['lng']}")
    return f"https://map.kakao.com/link/to/{destination}/from/{origin}"


def _fallback_places(place_type: str) -> list[dict]:
    if place_type == "bank":
        base = [
            ("KB국민은행 역삼동점", 37.5007, 127.0369, "서울 강남구 테헤란로"),
            ("신한은행 역삼금융센터", 37.5001, 127.0397, "서울 강남구 논현로"),
            ("우리은행 강남역지점", 37.4986, 127.0283, "서울 강남구 강남대로"),
        ]
    else:
        base = [
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
            "place_url": f"https://map.kakao.com/link/search/{quote(name)}",
            "direction_url": _direction_url(lat, lng),
        }
        for index, (name, lat, lng, address) in enumerate(base, 1)
    ]
