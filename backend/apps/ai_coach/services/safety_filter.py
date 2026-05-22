from __future__ import annotations

import re

MAX_REPLY_LENGTH = 420
MAX_ACTION_LENGTH = 90

BLOCKED_PHRASES = [
    "당첨됩니다",
    "당첨될 수 있습니다",
    "당첨 가능성이 높습니다",
    "신청 가능합니다",
    "신청할 수 있습니다",
    "대출 승인됩니다",
    "대출 가능합니다",
    "수익을 보장합니다",
    "정책 수급이 확정됩니다",
    "자격이 됩니다",
    "자격이 충족됩니다",
]


REPLACEMENTS = {
    "당첨됩니다": "당첨 가능성을 보장하지 않습니다",
    "당첨될 수 있습니다": "당첨 여부는 보장할 수 없습니다",
    "당첨 가능성이 높습니다": "당첨 가능성은 확정할 수 없습니다",
    "신청 가능합니다": "신청 가능성은 공식 공고 확인이 필요합니다",
    "신청할 수 있습니다": "신청 가능 여부는 공식 공고 확인이 필요합니다",
    "대출 승인됩니다": "대출 승인 여부는 금융기관 확인이 필요합니다",
    "대출 가능합니다": "대출 가능 여부는 금융기관 확인이 필요합니다",
    "수익을 보장합니다": "수익을 보장하지 않습니다",
    "정책 수급이 확정됩니다": "정책 수급 여부는 기관 확인이 필요합니다",
    "자격이 됩니다": "자격 여부는 공식 공고 확인이 필요합니다",
    "자격이 충족됩니다": "자격 충족 여부는 공식 공고 확인이 필요합니다",
}


def sanitize_text(value: str) -> str:
    next_value = re.sub(r"\s+", " ", value or "").strip()
    for phrase, replacement in REPLACEMENTS.items():
        next_value = next_value.replace(phrase, replacement)
    return next_value


def safety_flags(value: str) -> list[str]:
    return [phrase for phrase in BLOCKED_PHRASES if phrase in (value or "")]


def limit_text(value: str, *, max_length: int = MAX_REPLY_LENGTH) -> str:
    text = sanitize_text(value)
    if len(text) <= max_length:
        return text
    trimmed = text[: max_length + 1]
    sentence_end = max(trimmed.rfind("."), trimmed.rfind("요."), trimmed.rfind("다."))
    if sentence_end >= max_length * 0.55:
        return trimmed[: sentence_end + 1].strip()
    return text[:max_length].rstrip() + "..."


def sanitize_reply(value: str) -> str:
    text = limit_text(value, max_length=MAX_REPLY_LENGTH)
    required_notice = "공식 공고문 확인이 필요합니다."
    if "공식" not in text or "확인" not in text:
        suffix = " " + required_notice
        text = limit_text(text + suffix, max_length=MAX_REPLY_LENGTH)
    return text


def sanitize_actions(actions: list[str], *, limit: int = 3) -> list[str]:
    cleaned = [limit_text(str(action), max_length=MAX_ACTION_LENGTH) for action in actions]
    return [action for action in cleaned if action][:limit]


def sanitize_summary(summary: dict) -> dict:
    next_summary = summary.copy()
    for key in ["summary", "warning"]:
        next_summary[key] = sanitize_text(str(next_summary.get(key, "")))
    for key in ["todo_this_week", "official_checklist"]:
        next_summary[key] = [sanitize_text(str(item)) for item in next_summary.get(key, [])]
    return next_summary
