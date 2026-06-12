from __future__ import annotations

from apps.rules.regions import canonical_region

from dataclasses import dataclass
from typing import Any


SERVICE_TARGET_TYPES = {
    "public_sale",
    "newlywed_public_sale",
    "private_participation_public_sale",
}

HARD_DENY_KEYWORDS = [
    "행복주택",
    "국민임대",
    "영구임대",
    "매입임대",
    "장기전세",
    "든든전세",
    "전세",
    "신혼희망타운 임대",
    "분양전환",
    "10년공공임대",
    "10년 공공임대",
    "청년 공공주택",
    "일반매각",
    "분양광고",
    "오피스텔",
    "상가",
    "임대",
]

SCOPE_DENY_KEYWORDS = ["오피스텔", "상가", "토지"]
RESIDUAL_SALE_KEYWORDS = ["무순위", "잔여세대", "잔여주택", "선착순", "동호지정"]
LH_EXCLUDE_KEYWORDS = ("토지", "상가", "주차장", "주유소", "산업시설", "근린생활")
LH_HOUSING_KEYWORDS = ("주택", "임대", "분양", "행복", "국민", "영구", "매입", "전세", "공공")
RENTAL_KEYWORDS = ("임대", "전세", "매입", "분양전환")


@dataclass(frozen=True)
class NoticeClassification:
    ownership_type: str
    is_service_target: bool
    exclude_reason: str
    official_document_status: str = "not_requested"


def classify_notice_payload(notice: dict[str, Any]) -> NoticeClassification:
    text = notice_text(notice)
    normalized = text.replace(" ", "")

    scope_deny_keyword = first_keyword_match(text, SCOPE_DENY_KEYWORDS)
    if scope_deny_keyword:
        return NoticeClassification(
            ownership_type="excluded",
            is_service_target=False,
            exclude_reason=f"서비스 범위 밖의 공고: {scope_deny_keyword}",
        )

    deny_keyword = first_keyword_match(text, HARD_DENY_KEYWORDS)
    if deny_keyword:
        return NoticeClassification(
            ownership_type="excluded",
            is_service_target=False,
            exclude_reason=f"서비스 범위 밖의 공고: {deny_keyword}",
        )

    if "신혼희망타운" in normalized and "공공분양" in normalized:
        return NoticeClassification("newlywed_public_sale", True, "")

    if "민간참여" in normalized and "공공분양" in normalized:
        return NoticeClassification("private_participation_public_sale", True, "")

    if "공공분양주택" in normalized or "공공분양" in normalized or "분양주택" in normalized:
        return NoticeClassification("public_sale", True, "")

    residual_keyword = first_keyword_match(text, RESIDUAL_SALE_KEYWORDS)
    if residual_keyword:
        return NoticeClassification(
            ownership_type="unknown",
            is_service_target=False,
            exclude_reason=f"잔여/선착순 공고이나 공공분양 여부 확인 필요: {residual_keyword}",
        )

    return NoticeClassification(
        ownership_type="unknown",
        is_service_target=False,
        exclude_reason="소유형 공공분양 여부 확인 필요",
    )


def notice_text(notice: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "supply_type", "housing_type", "provider", "district"):
        value = notice.get(key)
        if value:
            parts.append(str(value))

    for tag in notice.get("tags") or []:
        parts.append(str(tag))

    source_meta = notice.get("source_meta") or {}
    if isinstance(source_meta, dict):
        for value in source_meta.values():
            if isinstance(value, (str, int, float)):
                parts.append(str(value))

    return " ".join(parts)


def first_keyword_match(text: str, keywords: list[str] | tuple[str, ...]) -> str:
    normalized = text.replace(" ", "")
    for keyword in keywords:
        if keyword in text or keyword.replace(" ", "") in normalized:
            return keyword
    return ""


def is_lh_housing_notice_text(text: str) -> bool:
    if any(keyword in text for keyword in LH_EXCLUDE_KEYWORDS):
        return False
    return any(keyword in text for keyword in LH_HOUSING_KEYWORDS)


def is_rental_text(text: str) -> bool:
    return any(keyword in text for keyword in RENTAL_KEYWORDS)


def lh_region_name(value: str) -> str:
    return canonical_region(value)


def lh_supply_type(raw_supply_type: str, title: str) -> str:
    text = f"{raw_supply_type} {title}"
    if "행복" in text or "청년" in text:
        return "청년 공공주택"
    if is_rental_text(text):
        return "공공임대"
    if "분양" in text:
        return "공공분양"
    return raw_supply_type[:40] or "LH 공고"


def lh_tags(raw_supply_type: str, title: str, region: str) -> list[str]:
    text = f"{raw_supply_type} {title}"
    tags = ["LH", region]
    if "청년" in text or "행복" in text:
        tags.append("청년")
    if "분양" in text and not is_rental_text(text):
        tags.append("공공분양")
    if is_rental_text(text):
        tags.append("공공임대")
    return list(dict.fromkeys(tag for tag in tags if tag))

