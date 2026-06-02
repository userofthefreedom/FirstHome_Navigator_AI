from __future__ import annotations

import re
from typing import Iterable


MONEY_TERMS = ("주택가격", "공급금액", "분양가격", "분양가", "계약금", "중도금", "잔금", "융자금", "납부")
ELIGIBILITY_TERMS = ("무주택", "소득", "자산", "청약통장", "거주", "우선공급", "특별공급", "일반공급")
DOCUMENT_TERMS = ("제출서류", "구비서류", "발급", "주민등록", "가족관계", "소득금액", "건강보험", "개인정보")
CAUTION_TERMS = ("유의사항", "정정", "변경", "발코니", "추가선택품목", "마이너스옵션", "사전청약")
PURPOSE_QUERIES = {
    "unit_options": ("주택형 전용면적 주택가격 공급금액 계약금 중도금 잔금 융자금", MONEY_TERMS),
    "payment_schedule": ("계약금 중도금 잔금 납부 납부일정 회차", MONEY_TERMS),
    "eligibility": ("무주택 소득 자산 청약통장 거주 우선공급 특별공급", ELIGIBILITY_TERMS),
    "required_documents": ("제출서류 구비서류 주민등록 가족관계 소득금액 건강보험 개인정보", DOCUMENT_TERMS),
    "cautions": ("유의사항 정정 변경 발코니 추가선택품목 마이너스옵션 사전청약", CAUTION_TERMS),
}


def query_terms(query: str, keywords: Iterable[str] = ()) -> tuple[str, ...]:
    return tuple(dict.fromkeys([*_terms(query), *[term for term in keywords if term]]))


def rank_document_chunk(text: str, block_type: str, query_terms: tuple[str, ...]) -> tuple[float, tuple[str, ...]]:
    normalized_text = _normalize(text)
    matched_terms: list[str] = []
    score = 0.0
    for term in query_terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        count = normalized_text.count(normalized_term)
        if count <= 0:
            continue
        matched_terms.append(term)
        score += 1 + min(count, 5) * 0.5

    if block_type == "table" and any(term in matched_terms for term in MONEY_TERMS):
        score += 2.0
    if any(term in matched_terms for term in DOCUMENT_TERMS) and ("서류" in normalized_text or "발급" in normalized_text):
        score += 1.25
    if any(term in matched_terms for term in CAUTION_TERMS) and ("유의" in normalized_text or "선택품목" in normalized_text):
        score += 1.0
    if "공급금액" in normalized_text and "납부" in normalized_text:
        score += 1.0
    if "제출서류" in normalized_text and "주민등록" in normalized_text:
        score += 1.0
    if re.search(r"\d{2,3}[A-Z]", text):
        score += 1.0
    if re.search(r"\d{1,3},\d{3}", text):
        score += 1.0
    return round(score, 3), tuple(matched_terms)


def _terms(value: str) -> list[str]:
    return [term for term in re.split(r"[^0-9A-Za-z가-힣]+", value or "") if len(term) >= 2]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()
