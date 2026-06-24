from __future__ import annotations

import re
from typing import Any

from apps.rules.confidence import checklist_confidence_from_evidence


PRICE_SECTION_KEYWORDS = ("주택가격", "계약금", "중도금", "잔금", "공급금액", "분양가격")
LOAN_KEYWORDS = ("융자금", "대출금", "주택도시기금")
MAX_EXTRACTED_OPTIONS = 50
ADDITIONAL_OPTION_KEYWORDS = ("추가선택품목", "발코니 확장", "시스템 에어컨", "플러스옵션")
REQUIRED_DOCUMENT_CANDIDATES = (
    ("당첨자 본인 신분증", ("당첨자 본인 신분증", "신분증")),
    ("주민등록표등본", ("주민등록표등본", "주민등록등본")),
    ("주민등록표초본", ("주민등록표초본", "주민등록초본")),
    (
        "개인정보 수집·이용 및 제3자 제공 동의서",
        ("개인정보 수집", "개인정보수집", "제3자 제공동의서", "제3자 제공 동의서"),
    ),
    ("가족관계증명서", ("가족관계증명서",)),
    ("혼인관계증명서", ("혼인관계증명서",)),
    ("출입국에 관한 사실증명", ("출입국에 관한 사실", "출입국사실증명")),
    ("재직증명서", ("재직증명서", "복무확인서")),
    ("임신증명서류 또는 출생증명서", ("임신증명서류", "출생증명서")),
    ("입양관계증명서", ("입양관계증명서", "친양자 입양관계")),
    ("장애인 등록증", ("장애인 등록증", "장애인등록증", "복지카드")),
    ("국내거소신고증 또는 외국인등록증", ("국내거소신고증", "외국인등록증")),
    ("소득세납부 입증서류", ("소득세납부 입증서류", "소득세 납부 입증서류")),
    ("소득금액증명원", ("소득금액증명원", "소득금액증명")),
    ("납부내역증명서", ("납부내역증명서", "납부내역 증명서")),
    ("근로소득원천징수영수증", ("근로소득원천징수영수증",)),
    ("건강보험자격득실확인서", ("건강보험자격득실확인서",)),
    ("사업자등록증명", ("사업자등록증명",)),
    ("한부모가족증명서", ("한부모가족증명서",)),
    ("계약금 입금 확인서류", ("계약금 입금 확인서류",)),
    (
        "주택취득 자금 조달 및 입주계획서",
        ("주택취득 자금 조달", "주택 취득 자금 조달", "자금조달계획서", "입주계획서"),
    ),
    ("위임장", ("위임장",)),
    ("인감증명서", ("인감증명서",)),
    ("본인서명사실확인서", ("본인서명사실확인서",)),
)
DOCUMENT_SECTION_KEYWORDS = ("제출서류", "구비서류", "계약서류", "당첨자 제출서류")

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
    return 100_000_000 <= value <= 2_000_000_000


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


def extract_required_documents_from_pages(pages: list[Any], *, limit: int = 18) -> list[str]:
    scored: dict[str, tuple[int, int]] = {}
    for page in pages:
        text = page.text or ""
        if not text:
            continue
        is_document_section = any(keyword in text for keyword in DOCUMENT_SECTION_KEYWORDS)
        for index, (label, aliases) in enumerate(REQUIRED_DOCUMENT_CANDIDATES):
            if not any(alias in text for alias in aliases):
                continue
            score = 20 if is_document_section else 4
            if page.page_no >= 20:
                score += 5
            if "필수" in text:
                score += 3
            previous = scored.get(label)
            value = (score, -index)
            if previous is None or value > previous:
                scored[label] = value

    ordered = sorted(scored.items(), key=lambda item: (item[1][0], item[1][1]), reverse=True)
    return [label for label, _score in ordered[:limit]]


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
        confidence = checklist_confidence_from_evidence(
            keyword_score=keyword_score,
            phrase_score=phrase_score,
            page_no=page.page_no,
            has_definition_marker=("기준" in text or "판정" in text),
        )
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
