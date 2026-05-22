from __future__ import annotations

from apps.notice_docs.services.extractors import ExtractedUnitOption


def validate_unit_options(options: list[ExtractedUnitOption]) -> list[ExtractedUnitOption]:
    for option in options:
        option.validation_warnings = _warnings_for_option(option)
        if option.validation_warnings:
            option.confidence = min(option.confidence, 0.49)
    return options


def extraction_status(options: list[ExtractedUnitOption]) -> str:
    if not options:
        return "failed"
    if any(option.validation_warnings for option in options):
        return "needs_review"
    return "valid"


def extraction_confidence(options: list[ExtractedUnitOption]) -> float:
    if not options:
        return 0
    return round(sum(option.confidence for option in options) / len(options), 2)


def _warnings_for_option(option: ExtractedUnitOption) -> list[str]:
    warnings: list[str] = []
    if not option.unit_type:
        warnings.append("주택형이 비어 있습니다.")
    if option.exclusive_area_m2 <= 0:
        warnings.append("전용면적을 확인할 수 없습니다.")
    if option.base_price <= 0:
        warnings.append("분양가를 확인할 수 없습니다.")
    if not option.payment_schedules:
        warnings.append("납부 일정을 확인할 수 없습니다.")
    if not option.source_text:
        warnings.append("근거 문장이 없습니다.")

    payment_total = sum(schedule.amount for schedule in option.payment_schedules)
    compared_price = max(0, option.base_price - option.loan_amount)
    if option.base_price > 0 and payment_total > 0 and compared_price > 0:
        difference_ratio = abs(payment_total - compared_price) / compared_price
        if difference_ratio > 0.08:
            warnings.append("계약금·중도금·잔금 합계와 분양가 차이가 큽니다.")

    return warnings
