from __future__ import annotations

from typing import Any


OPTION_CONFIDENCE_BASE = 0.55
OPTION_CONFIDENCE_CAP = 0.94
OPTION_REVIEW_CAP = 0.49


def option_confidence_from_quality(
    *,
    base_confidence: float,
    has_price: bool,
    has_schedule: bool,
    has_source: bool,
    has_required_schedule_types: bool,
    has_loan_signal: bool = False,
    validation_warnings: list[str] | None = None,
) -> float:
    score = max(float(base_confidence or 0), OPTION_CONFIDENCE_BASE)
    score += 0.04 if has_price else -0.12
    score += 0.05 if has_schedule else -0.12
    score += 0.03 if has_source else -0.06
    score += 0.04 if has_required_schedule_types else -0.04
    score += 0.02 if has_loan_signal else 0
    warnings = validation_warnings or []
    if warnings:
        score = min(score - min(0.18, 0.04 * len(warnings)), OPTION_REVIEW_CAP)
    return round(min(OPTION_CONFIDENCE_CAP, max(0, score)), 2)


def checklist_confidence_from_evidence(
    *,
    keyword_score: int,
    phrase_score: int,
    page_no: int,
    has_definition_marker: bool,
) -> float:
    confidence = 0.62
    confidence += min(0.16, phrase_score * 0.04)
    confidence += min(0.12, keyword_score * 0.008)
    if page_no > 4:
        confidence += 0.03
    if has_definition_marker:
        confidence += 0.02
    return round(min(0.91, max(0.58, confidence)), 2)


def aggregate_extraction_confidence(options: list[Any]) -> float:
    if not options:
        return 0
    return round(sum(float(getattr(option, "confidence", 0) or 0) for option in options) / len(options), 2)


def option_confidence_explanation(option: Any) -> list[str]:
    reasons: list[str] = []
    if int(getattr(option, "base_price", 0) or 0) > 0:
        reasons.append("분양가 표에서 금액을 확인했습니다.")
    schedules = getattr(option, "payment_schedules", []) or []
    if hasattr(schedules, "all"):
        schedules = list(schedules.all())
    if list(schedules):
        reasons.append("계약금/중도금/잔금 일정을 함께 확인했습니다.")
    if int(getattr(option, "loan_amount", 0) or 0) > 0:
        reasons.append("융자금 항목을 별도 금액으로 분리했습니다.")
    if getattr(option, "source_page", None):
        reasons.append(f"{getattr(option, 'source_page')}쪽 원문에서 추출했습니다.")
    warnings = list(getattr(option, "validation_warnings", []) or [])
    reasons.extend(warnings)
    return reasons[:5]
