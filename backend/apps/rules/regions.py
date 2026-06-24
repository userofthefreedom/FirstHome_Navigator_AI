from __future__ import annotations

from typing import Any


REGION_ALIASES = {
    "서울": ("서울", "서울특별시"),
    "부산": ("부산", "부산광역시"),
    "대구": ("대구", "대구광역시"),
    "인천": ("인천", "인천광역시"),
    "광주": ("광주", "광주광역시"),
    "대전": ("대전", "대전광역시"),
    "울산": ("울산", "울산광역시"),
    "세종": ("세종", "세종특별자치시"),
    "경기": ("경기", "경기도", "경기 남부", "경기 북부"),
    "경기 남부": ("경기 남부", "경기남부", "경기도"),
    "경기 북부": ("경기 북부", "경기북부", "경기도"),
    "강원": ("강원", "강원도", "강원특별자치도"),
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
    "제주": ("제주", "제주도", "제주특별자치도"),
}

GYEONGGI_NORTH_PLACES = (
    "고양",
    "김포",
    "남양주",
    "파주",
    "의정부",
    "양주시",
    "구리",
    "포천",
    "동두천",
    "가평",
    "연천",
)

GYEONGGI_SOUTH_PLACES = (
    "수원",
    "성남",
    "용인",
    "화성",
    "동탄",
    "평택",
    "오산",
    "안성시",
    "이천",
    "여주",
    "광주시",
    "하남",
    "과천",
    "안양",
    "군포",
    "의왕",
    "안산",
    "시흥",
    "광명",
    "부천",
    "양평",
)

LOCAL_REGION_ALIASES = {
    "인천": (
        "강화군",
        "옹진",
        "옹진군",
        "미추홀",
        "미추홀구",
        "연수구",
        "남동구",
        "부평",
        "부평구",
        "계양구",
    ),
    "충남": (
        "태안",
        "태안군",
        "홍성",
        "홍성군",
        "천안시",
        "공주시",
        "보령시",
        "아산시",
        "서산시",
        "논산시",
        "계룡시",
        "당진시",
        "금산군",
        "부여군",
        "서천군",
        "청양군",
        "예산군",
    ),
    "충북": ("청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"),
    "전북": ("전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"),
    "전남": ("목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"),
    "경북": ("포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"),
    "경남": ("창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"),
    "강원": ("춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"),
    "제주": ("제주시", "서귀포시"),
}


def normalize_region_key(value: Any) -> str:
    return "".join(str(value or "").split())


def gyeonggi_subregion_from_text(*parts: Any) -> str | None:
    text = " ".join(str(part or "") for part in parts)
    compact_text = normalize_region_key(text)
    if not text:
        return None
    if any(place in text for place in GYEONGGI_NORTH_PLACES):
        return "경기 북부"
    if any(place in text for place in GYEONGGI_SOUTH_PLACES):
        return "경기 남부"
    if "경기북부" in compact_text:
        return "경기 북부"
    if "경기남부" in compact_text:
        return "경기 남부"
    return None


def infer_region_from_text(*parts: Any) -> list[str]:
    text = " ".join(str(part or "") for part in parts)
    text_key = normalize_region_key(text)
    if not text_key:
        return []

    matched: list[str] = []

    subregion = gyeonggi_subregion_from_text(text)
    if subregion:
        matched.append(subregion)

    for label, aliases in REGION_ALIASES.items():
        if any(
            normalize_region_key(alias) in text_key
            for alias in aliases
            if len(normalize_region_key(alias)) >= 3
        ):
            matched.append(label)

    for label, aliases in LOCAL_REGION_ALIASES.items():
        if any(normalize_region_key(alias) in text_key for alias in aliases if alias):
            matched.append(label)

    return list(dict.fromkeys(matched))


def canonical_region(region: Any, *context: Any, default: str = "전국") -> str:
    raw_region = str(region or "").strip()
    text = " ".join(str(part or "") for part in (raw_region, *context))
    text_key = normalize_region_key(text)
    if "경기" in text_key or "경기도" in text_key:
        return gyeonggi_subregion_from_text(text) or "경기 남부"

    region_key = normalize_region_key(raw_region)
    for label, aliases in REGION_ALIASES.items():
        if any(normalize_region_key(alias) in region_key for alias in aliases):
            return label
    return raw_region or default


def notice_region(notice: dict[str, Any]) -> str:
    return canonical_region(
        notice.get("region"),
        notice.get("district"),
        notice.get("title"),
        _notice_site_value(notice),
    )


def notice_matches_preferred_region(notice: dict[str, Any], preferred_region: Any) -> bool:
    preferred_key = normalize_region_key(preferred_region)
    if not preferred_key:
        return False
    text = " ".join(
        str(part or "")
        for part in (
            notice.get("region"),
            notice.get("district"),
            notice.get("title"),
            _notice_site_value(notice),
        )
    )
    text_key = normalize_region_key(text)
    region_key = normalize_region_key(notice.get("region"))

    if preferred_key in {"경기", "경기도"}:
        return "경기" in text_key or "경기도" in text_key
    if preferred_key in {"경기북부", "경기남부"}:
        target_subregion = gyeonggi_subregion_from_text(text)
        if target_subregion:
            return normalize_region_key(target_subregion) == preferred_key
        return region_key in {preferred_key, "경기", "경기도"}

    aliases = REGION_ALIASES.get(str(preferred_region).strip(), (preferred_region,))
    return any(normalize_region_key(alias) in text_key for alias in aliases if alias)


def region_matches(target_region: Any, preferred_region: Any) -> bool:
    target_key = normalize_region_key(target_region)
    preferred_key = normalize_region_key(preferred_region)
    if not target_key or not preferred_key:
        return False
    if preferred_key in {"경기", "경기도"}:
        return "경기" in target_key or "경기도" in target_key
    if preferred_key in {"경기북부", "경기남부"}:
        target_subregion = gyeonggi_subregion_from_text(target_region)
        if target_subregion:
            return normalize_region_key(target_subregion) == preferred_key
        return target_key == preferred_key
    aliases = REGION_ALIASES.get(str(preferred_region).strip(), (preferred_region,))
    return any(normalize_region_key(alias) in target_key for alias in aliases if alias)


def _notice_site_value(notice: dict[str, Any]) -> str:
    source_meta = notice.get("source_meta")
    supply_summary = source_meta.get("supply_summary") if isinstance(source_meta, dict) else None
    if isinstance(supply_summary, dict):
        return str(supply_summary.get("district") or "")
    return ""
