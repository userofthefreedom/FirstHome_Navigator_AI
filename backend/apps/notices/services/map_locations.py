from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests
from django.conf import settings


SEOUL_CENTER = {"lat": 37.566826, "lng": 126.978656}

REGION_CENTERS: dict[str, dict[str, float]] = {
    "서울": SEOUL_CENTER,
    "부산": {"lat": 35.179554, "lng": 129.075642},
    "대구": {"lat": 35.871435, "lng": 128.601445},
    "인천": {"lat": 37.456256, "lng": 126.705206},
    "광주": {"lat": 35.159545, "lng": 126.852601},
    "대전": {"lat": 36.350412, "lng": 127.384548},
    "울산": {"lat": 35.538377, "lng": 129.311360},
    "세종": {"lat": 36.480132, "lng": 127.289021},
    "경기": {"lat": 37.413800, "lng": 127.518300},
    "경기 남부": {"lat": 37.263573, "lng": 127.028601},
    "경기 북부": {"lat": 37.738098, "lng": 127.033682},
    "강원": {"lat": 37.885621, "lng": 127.729970},
    "충북": {"lat": 36.635680, "lng": 127.491384},
    "충남": {"lat": 36.658829, "lng": 126.672849},
    "전북": {"lat": 35.824224, "lng": 127.147953},
    "전남": {"lat": 34.816095, "lng": 126.462924},
    "경북": {"lat": 36.576032, "lng": 128.505599},
    "경남": {"lat": 35.238294, "lng": 128.692397},
    "제주": {"lat": 33.499621, "lng": 126.531188},
}

PLACE_CENTERS: dict[str, dict[str, float]] = {
    "고덕강일": {"lat": 37.563028, "lng": 127.173133},
    "강동구": {"lat": 37.530125, "lng": 127.123762},
    "마곡": {"lat": 37.566447, "lng": 126.827540},
    "위례": {"lat": 37.471061, "lng": 127.142983},
    "수서": {"lat": 37.487418, "lng": 127.101890},
    "항동": {"lat": 37.481092, "lng": 126.823421},
    "에코델타": {"lat": 35.152265, "lng": 128.910410},
    "명지": {"lat": 35.108787, "lng": 128.926311},
    "일광": {"lat": 35.264263, "lng": 129.233225},
    "센텀": {"lat": 35.169702, "lng": 129.130013},
    "온천장": {"lat": 35.221461, "lng": 129.086154},
    "연호": {"lat": 35.846277, "lng": 128.704914},
    "금호워터폴리스": {"lat": 35.910439, "lng": 128.606306},
    "대구대공원": {"lat": 35.827347, "lng": 128.674503},
    "안심뉴타운": {"lat": 35.873074, "lng": 128.723978},
    "테크노폴리스": {"lat": 35.693699, "lng": 128.458995},
    "검단": {"lat": 37.597476, "lng": 126.657904},
    "계양": {"lat": 37.538426, "lng": 126.737767},
    "송도": {"lat": 37.382268, "lng": 126.643433},
    "영종": {"lat": 37.489363, "lng": 126.531554},
    "루원": {"lat": 37.515811, "lng": 126.676282},
    "선운": {"lat": 35.148855, "lng": 126.777921},
    "첨단": {"lat": 35.222624, "lng": 126.843373},
    "효천": {"lat": 35.094568, "lng": 126.874364},
    "송정역세권": {"lat": 35.137904, "lng": 126.790623},
    "평동": {"lat": 35.124544, "lng": 126.768612},
    "도안": {"lat": 36.329778, "lng": 127.339823},
    "갑천": {"lat": 36.344068, "lng": 127.371385},
    "복합터미널": {"lat": 36.350111, "lng": 127.436722},
    "연축": {"lat": 36.392067, "lng": 127.421933},
    "관저": {"lat": 36.299865, "lng": 127.337856},
    "다운2": {"lat": 35.571226, "lng": 129.263365},
    "태화강변": {"lat": 35.551362, "lng": 129.318844},
    "우정혁신": {"lat": 35.558470, "lng": 129.291076},
    "송대": {"lat": 35.572896, "lng": 129.241931},
    "북울산역": {"lat": 35.637132, "lng": 129.350956},
    "5-1생활권": {"lat": 36.529054, "lng": 127.299141},
    "6-3생활권": {"lat": 36.574474, "lng": 127.290411},
    "4-2생활권": {"lat": 36.476452, "lng": 127.286434},
    "조치원": {"lat": 36.601263, "lng": 127.297252},
    "집현": {"lat": 36.475803, "lng": 127.298896},
    "동탄2": {"lat": 37.199494, "lng": 127.098902},
    "왕숙": {"lat": 37.660071, "lng": 127.174088},
    "창릉": {"lat": 37.637789, "lng": 126.880101},
    "교산": {"lat": 37.517731, "lng": 127.208540},
    "장상": {"lat": 37.346910, "lng": 126.868542},
    "춘천": {"lat": 37.881315, "lng": 127.729970},
    "원주": {"lat": 37.341466, "lng": 127.920455},
    "강릉": {"lat": 37.751854, "lng": 128.876057},
    "속초": {"lat": 38.207014, "lng": 128.591849},
    "동해": {"lat": 37.524758, "lng": 129.114262},
    "청주": {"lat": 36.642434, "lng": 127.489032},
    "충주": {"lat": 36.991011, "lng": 127.925950},
    "제천": {"lat": 37.132582, "lng": 128.190948},
    "음성": {"lat": 36.940282, "lng": 127.690607},
    "진천": {"lat": 36.854642, "lng": 127.435536},
    "천안": {"lat": 36.815129, "lng": 127.113893},
    "아산": {"lat": 36.789844, "lng": 127.001849},
    "내포": {"lat": 36.664013, "lng": 126.673886},
    "당진": {"lat": 36.893098, "lng": 126.628327},
    "공주": {"lat": 36.446534, "lng": 127.119153},
    "전주": {"lat": 35.824224, "lng": 127.147953},
    "익산": {"lat": 35.948285, "lng": 126.957599},
    "군산": {"lat": 35.967626, "lng": 126.736875},
    "완주": {"lat": 35.904693, "lng": 127.162104},
    "정읍": {"lat": 35.569867, "lng": 126.856039},
    "무안": {"lat": 34.990342, "lng": 126.481722},
    "순천": {"lat": 34.950637, "lng": 127.487213},
    "여수": {"lat": 34.760374, "lng": 127.662222},
    "목포": {"lat": 34.811835, "lng": 126.392166},
    "나주": {"lat": 35.015814, "lng": 126.710815},
    "포항": {"lat": 36.019018, "lng": 129.343480},
    "구미": {"lat": 36.119598, "lng": 128.344344},
    "안동": {"lat": 36.568354, "lng": 128.729357},
    "경산": {"lat": 35.825057, "lng": 128.741544},
    "김천": {"lat": 36.139773, "lng": 128.113614},
    "창원": {"lat": 35.227507, "lng": 128.681229},
    "김해": {"lat": 35.228545, "lng": 128.889352},
    "양산": {"lat": 35.335036, "lng": 129.037346},
    "진주": {"lat": 35.180260, "lng": 128.107621},
    "거제": {"lat": 34.880642, "lng": 128.621082},
    "제주시": {"lat": 33.499621, "lng": 126.531188},
    "서귀포": {"lat": 33.253925, "lng": 126.559785},
}


def resolve_notice_location(notice: dict[str, Any]) -> dict[str, Any]:
    lat = _float_or_none(notice.get("latitude"))
    lng = _float_or_none(notice.get("longitude"))
    label = str(notice.get("location_label") or notice.get("district") or notice.get("region") or "").strip()
    if lat is not None and lng is not None:
        return {"lat": lat, "lng": lng, "label": label, "quality": notice.get("geocode_quality") or "exact"}

    meta_location = _source_meta_location(notice)
    if meta_location:
        return meta_location

    text = f"{notice.get('region', '')} {notice.get('district', '')} {notice.get('title', '')}"
    for key, center in sorted(PLACE_CENTERS.items(), key=lambda item: len(item[0]), reverse=True):
        if key in text:
            return {"lat": center["lat"], "lng": center["lng"], "label": label or key, "quality": "district"}

    center = _region_center(str(notice.get("region") or ""))
    return {"lat": center["lat"], "lng": center["lng"], "label": label or notice.get("region") or "전국", "quality": "region_fallback"}


def offset_location(location: dict[str, Any], index: int) -> dict[str, Any]:
    if index <= 0:
        return location
    # Spread notices that share fallback coordinates so Kakao markers remain selectable.
    ring = index % 8
    distance = 0.004 + (index // 8) * 0.002
    offsets = [
        (0, distance),
        (distance, distance),
        (distance, 0),
        (distance, -distance),
        (0, -distance),
        (-distance, -distance),
        (-distance, 0),
        (-distance, distance),
    ]
    lat_offset, lng_offset = offsets[ring]
    return {**location, "lat": location["lat"] + lat_offset, "lng": location["lng"] + lng_offset}


def kakao_geocode(query: str) -> dict[str, Any] | None:
    api_key = settings.EXTERNAL_API_KEYS.get("KAKAO_REST_API_KEY", "")
    query = query.strip()
    if not api_key or not query:
        return None

    headers = {"Authorization": f"KakaoAK {api_key}"}
    for url in (
        "https://dapi.kakao.com/v2/local/search/address.json",
        "https://dapi.kakao.com/v2/local/search/keyword.json",
    ):
        response = requests.get(url, params={"query": query, "size": 1}, headers=headers, timeout=10)
        response.raise_for_status()
        documents = response.json().get("documents") or []
        if not documents:
            continue
        first = documents[0]
        return {
            "lat": float(first["y"]),
            "lng": float(first["x"]),
            "label": first.get("address_name") or query,
            "quality": "kakao_rest",
        }
    return None


def _source_meta_location(notice: dict[str, Any]) -> dict[str, Any] | None:
    source_meta = notice.get("source_meta")
    if not isinstance(source_meta, dict):
        return None
    candidates = [
        source_meta.get("map_location"),
        source_meta.get("location"),
        source_meta.get("coordinates"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        lat = _float_or_none(candidate.get("lat") or candidate.get("latitude") or candidate.get("y"))
        lng = _float_or_none(candidate.get("lng") or candidate.get("longitude") or candidate.get("x"))
        if lat is None or lng is None:
            continue
        label = str(candidate.get("label") or candidate.get("address") or notice.get("district") or "").strip()
        return {"lat": lat, "lng": lng, "label": label, "quality": candidate.get("quality") or "exact"}
    return None


def _region_center(region: str) -> dict[str, float]:
    if region in REGION_CENTERS:
        return REGION_CENTERS[region]
    if "경기" in region and "북" in region:
        return REGION_CENTERS["경기 북부"]
    if "경기" in region:
        return REGION_CENTERS["경기 남부"]
    for key, center in REGION_CENTERS.items():
        if key and key in region:
            return center
    return SEOUL_CENTER


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
