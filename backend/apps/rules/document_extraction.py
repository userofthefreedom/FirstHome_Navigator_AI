from __future__ import annotations

import re
from typing import Any


PRICE_SECTION_KEYWORDS = ("주택가격", "계약금", "중도금", "잔금", "공급금액", "분양가격")
LOAN_KEYWORDS = ("융자금", "대출금", "주택도시기금")
MAX_EXTRACTED_OPTIONS = 50
ADDITIONAL_OPTION_KEYWORDS = ("추가선택품목", "발코니 확장", "시스템 에어컨", "플러스옵션")

CHECKLIST_RULES = [
    (
        "homeless",
        "무주택 기준 확인",
        ("무주택세대구성원", "주택소유여부", "무주택", "주택소유"),
        ("무주택세대구성원 및 주택소유여부 판정 기준", "무주택세대구성원", "주택소유여부 판정"),
    ),
    (
        "income",
        "소득·자산 기준 확인",
        ("소득기준", "자산기준", "소득", "자산"),
        ("소득기준", "자산기준", "소득 및 자산", "총자산"),
    ),
    (
        "subscription",
        "청약통장 요건 확인",
        ("입주자저축", "청약통장", "납입", "가입"),
        ("입주자저축", "청약통장", "납입인정", "가입기간"),
    ),
    (
        "residency",
        "지역 우선공급 확인",
        ("지역우선공급", "우선공급", "거주자", "거주"),
        ("지역우선공급", "해당 주택건설지역", "기타지역", "거주자"),
    ),
]


def is_price_section(text: str) -> bool:
    return sum(1 for keyword in PRICE_SECTION_KEYWORDS if keyword in text) >= 3


def is_additional_option_section(text: str) -> bool:
    return any(keyword in text for keyword in ADDITIONAL_OPTION_KEYWORDS) and "주택가격" not in text


def is_valid_exclusive_area(value: float) -> bool:
    return 20 <= value <= 120


def is_valid_base_price(value: int) -> bool:
    return value >= 100_000_000


def has_loan_keyword(text: str) -> bool:
    return any(keyword in text for keyword in LOAN_KEYWORDS)


def option_type_from_text(text: str) -> str:
    if "사전청약" in text:
        return "pre_subscription"
    if re.search(r"계약금\s*\(5%\)", text):
        return "pre_subscription"
    if "일반 당첨자" in text or "특별공급" in text or "일반공급" in text:
        return "general_supply"
    if re.search(r"계약금\s*\(10%\)", text):
        return "general_supply"
    return "minus" if "마이너스" in text else "basic"


def extract_checklist_items_from_pages(pages: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for category, title, keywords, preferred_phrases in CHECKLIST_RULES:
        evidence = best_checklist_evidence(pages, keywords, preferred_phrases)
        if not evidence:
            continue
        items.append(
            {
                "category": category,
                "title": title,
                "condition_text": "",
                "evidence_text": evidence["text"],
                "confidence": evidence["confidence"],
                "page_no": evidence["page_no"],
            }
        )
    return items


def best_checklist_evidence(
    pages: list[Any],
    keywords: tuple[str, ...],
    preferred_phrases: tuple[str, ...],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for page in pages:
        text = page.text or ""
        keyword_score = sum(text.count(keyword) for keyword in keywords)
        phrase_score = sum(1 for phrase in preferred_phrases if phrase in text)
        if keyword_score <= 0 and phrase_score <= 0:
            continue

        score = keyword_score + phrase_score * 12
        if page.page_no > 4:
            score += 4
        elif page.page_no <= 2 and phrase_score == 0:
            score -= 8
        if "기준" in text or "판정" in text:
            score += 3

        needle = next((phrase for phrase in preferred_phrases if phrase in text), None)
        if needle is None:
            needle = max(keywords, key=lambda keyword: text.count(keyword))
        confidence = 0.62
        confidence += min(0.16, phrase_score * 0.04)
        confidence += min(0.12, keyword_score * 0.008)
        if page.page_no > 4:
            confidence += 0.03
        if "기준" in text or "판정" in text:
            confidence += 0.02
        confidence = min(0.91, max(0.58, confidence))
        candidate = {
            "page_no": page.page_no,
            "text": source_snippet(text, needle),
            "confidence": round(confidence, 2),
            "score": score,
        }
        if best is None or (candidate["score"], -candidate["page_no"]) > (best["score"], -best["page_no"]):
            best = candidate
    if best is None:
        return None
    return {key: best[key] for key in ("page_no", "text", "confidence")}


def source_snippet(text: str, needle: str, *, radius: int = 90) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    index = compact.find(needle)
    if index < 0:
        return compact[: radius * 2]
    start = max(0, index - radius)
    end = min(len(compact), index + len(needle) + radius)
    return compact[start:end]

