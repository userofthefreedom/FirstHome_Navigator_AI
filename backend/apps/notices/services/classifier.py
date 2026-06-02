from __future__ import annotations

from apps.rules.notice_classification import (
    HARD_DENY_KEYWORDS,
    RESIDUAL_SALE_KEYWORDS,
    SCOPE_DENY_KEYWORDS,
    SERVICE_TARGET_TYPES,
    NoticeClassification,
    classify_notice_payload,
    first_keyword_match,
    notice_text,
)


def _notice_text(notice: dict) -> str:
    return notice_text(notice)


def _first_match(text: str, keywords: list[str]) -> str:
    return first_keyword_match(text, keywords)
