from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SERVICE_TARGET_TYPES = {
    "public_sale",
    "newlywed_public_sale",
    "private_participation_public_sale",
}

DENY_KEYWORDS = [
    "임대",
    "행복주택",
    "국민임대",
    "영구임대",
    "매입임대",
    "전세",
    "장기전세",
    "든든전세",
    "분양전환",
    "10년공공임대",
    "10년 공공임대",
    "청년 공공주택",
    "일반매각",
    "오피스텔 분양광고",
]


@dataclass(frozen=True)
class NoticeClassification:
    ownership_type: str
    is_service_target: bool
    exclude_reason: str
    official_document_status: str = "not_requested"


def classify_notice_payload(notice: dict[str, Any]) -> NoticeClassification:
    text = _notice_text(notice)
    normalized = text.replace(" ", "")

    deny_keyword = _first_match(text, DENY_KEYWORDS)
    if deny_keyword:
        return NoticeClassification(
            ownership_type="excluded",
            is_service_target=False,
            exclude_reason=f"서비스 범위 밖 공고: {deny_keyword}",
        )

    if "신혼희망타운" in text and "공공분양" in text:
        return NoticeClassification(
            ownership_type="newlywed_public_sale",
            is_service_target=True,
            exclude_reason="",
        )

    if "민간참여형" in text and "공공분양" in text:
        return NoticeClassification(
            ownership_type="private_participation_public_sale",
            is_service_target=True,
            exclude_reason="",
        )

    if "공공분양주택" in normalized or "공공분양" in text or "뉴홈" in text:
        return NoticeClassification(
            ownership_type="public_sale",
            is_service_target=True,
            exclude_reason="",
        )

    return NoticeClassification(
        ownership_type="unknown",
        is_service_target=False,
        exclude_reason="소유형 공공분양 여부 확인 필요",
    )


def _notice_text(notice: dict[str, Any]) -> str:
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


def _first_match(text: str, keywords: list[str]) -> str:
    normalized = text.replace(" ", "")
    for keyword in keywords:
        if keyword in text or keyword.replace(" ", "") in normalized:
            return keyword
    return ""
