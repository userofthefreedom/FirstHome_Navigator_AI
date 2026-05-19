from __future__ import annotations


BLOCKED_PHRASES = [
    "당첨됩니다",
    "신청 가능합니다",
    "대출 승인됩니다",
    "수익을 보장합니다",
    "정책 수급이 확정됩니다",
]


REPLACEMENTS = {
    "당첨됩니다": "당첨 가능성을 보장하지 않습니다",
    "신청 가능합니다": "신청 가능성은 공식 공고 확인이 필요합니다",
    "대출 승인됩니다": "대출 승인 여부는 금융기관 확인이 필요합니다",
    "수익을 보장합니다": "수익을 보장하지 않습니다",
    "정책 수급이 확정됩니다": "정책 수급 여부는 기관 확인이 필요합니다",
}


def sanitize_text(value: str) -> str:
    next_value = value
    for phrase, replacement in REPLACEMENTS.items():
        next_value = next_value.replace(phrase, replacement)
    return next_value


def sanitize_summary(summary: dict) -> dict:
    next_summary = summary.copy()
    for key in ["summary", "warning"]:
        next_summary[key] = sanitize_text(str(next_summary.get(key, "")))
    for key in ["todo_this_week", "official_checklist"]:
        next_summary[key] = [sanitize_text(str(item)) for item in next_summary.get(key, [])]
    return next_summary
