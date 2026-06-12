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
        return target_key in {"경기", "경기도", preferred_key}
    aliases = REGION_ALIASES.get(str(preferred_region).strip(), (preferred_region,))
    return any(normalize_region_key(alias) in target_key for alias in aliases if alias)


def _notice_site_value(notice: dict[str, Any]) -> str:
    source_meta = notice.get("source_meta")
    supply_summary = source_meta.get("supply_summary") if isinstance(source_meta, dict) else None
    if isinstance(supply_summary, dict):
        return str(supply_summary.get("district") or "")
    return ""
