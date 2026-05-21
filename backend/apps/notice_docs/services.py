from __future__ import annotations

import re
from datetime import date, timedelta

from django.utils import timezone

from apps.notice_docs.models import (
    EligibilityChecklist,
    HousingUnitOption,
    NoticeDocument,
    NoticeExtraction,
    PaymentSchedule,
)
from apps.notices.models import HousingNotice


def analyze_notice_with_mock_data(notice: HousingNotice) -> dict:
    document = _document_for_notice(notice)
    document.status = "pending"
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])

    extraction = NoticeExtraction.objects.create(
        notice=notice,
        document=document,
        schema_version="mock-v1",
        status="mock",
        confidence=0.62,
        raw_json={
            "source": "mock",
            "reason": "LLM 연결 전 샘플 추출 데이터",
            "notice_id": notice.id,
        },
    )

    options = _mock_unit_options(notice, document, extraction)
    _mock_checklists(notice, document)

    now = timezone.now()
    document.status = "analyzed"
    document.analyzed_at = now
    document.save(update_fields=["status", "analyzed_at", "updated_at"])

    notice.official_document_status = "analyzed"
    notice.save(update_fields=["official_document_status", "updated_at"])

    return {
        "document": document,
        "extraction": extraction,
        "unit_options": options,
    }


def document_status(notice: HousingNotice) -> dict:
    documents = list(notice.documents.order_by("-updated_at", "-id"))
    unit_options = HousingUnitOption.objects.filter(notice=notice)
    return {
        "notice_id": notice.id,
        "official_document_status": notice.official_document_status,
        "document_count": len(documents),
        "unit_option_count": unit_options.count(),
        "analyzed_option_count": unit_options.filter(confidence__gt=0).count(),
        "documents": documents,
    }


def _document_for_notice(notice: HousingNotice) -> NoticeDocument:
    document_url = notice.source_url or ""
    document, _created = NoticeDocument.objects.get_or_create(
        notice=notice,
        document_url=document_url,
        defaults={
            "provider": notice.provider,
            "file_name": _document_name(notice),
            "source_url": notice.source_url,
            "status": "discovered",
        },
    )
    changed = False
    if not document.file_name:
        document.file_name = _document_name(notice)
        changed = True
    if not document.provider:
        document.provider = notice.provider
        changed = True
    if not document.source_url:
        document.source_url = notice.source_url
        changed = True
    if changed:
        document.save(update_fields=["file_name", "provider", "source_url", "updated_at"])
    return document


def _document_name(notice: HousingNotice) -> str:
    title = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", notice.title).strip("_")
    return f"{title[:80]}_mock.pdf" if title else "official_notice_mock.pdf"


def _mock_unit_options(
    notice: HousingNotice,
    document: NoticeDocument,
    extraction: NoticeExtraction,
) -> list[HousingUnitOption]:
    base_area = _area_m2(notice.area) or 59
    base_price = int(notice.price or 0)
    area_candidates = _area_candidates(base_area)
    options: list[HousingUnitOption] = []

    for index, area in enumerate(area_candidates, start=1):
        unit_type = f"{int(round(area))}A"
        price = _price_for_area(base_price, base_area, area)
        option, _created = HousingUnitOption.objects.update_or_create(
            notice=notice,
            unit_type=unit_type,
            floor_group="대표",
            option_type="basic",
            defaults={
                "document": document,
                "extraction": extraction,
                "exclusive_area_m2": area,
                "base_price": price,
                "loan_amount": 0,
                "balcony_extension_price": 0,
                "confidence": 0.55 if price else 0.35,
                "source_page": 4,
                "source_text": "mock: 공식 공고문 표 추출 전 대표 면적/가격 기반 임시 옵션",
            },
        )
        _replace_payment_schedule(option, notice, price)
        options.append(option)
        if index >= 3:
            break
    return options


def _replace_payment_schedule(option: HousingUnitOption, notice: HousingNotice, price: int) -> None:
    option.payment_schedules.all().delete()
    contract_rate = float(notice.contract_rate or 0.1)
    down_payment = round(price * contract_rate)
    middle_payment = round(price * 0.6)
    final_payment = max(0, price - down_payment - middle_payment)
    contract_date = _as_date(notice.contract_date)
    middle_date = contract_date + timedelta(days=180) if contract_date else None

    rows = [
        ("청약 접수 마감", _as_date(notice.application_deadline), 0, "application", 1),
        ("당첨자 발표", _as_date(notice.winner_date), 0, "winner", 2),
        ("계약금", contract_date, down_payment, "down_payment", 3),
        ("중도금 대표 회차", middle_date, middle_payment, "middle_payment", 4),
        ("잔금", None, final_payment, "final_payment", 5),
    ]
    for label, due_date, amount, payment_type, sequence in rows:
        PaymentSchedule.objects.create(
            unit_option=option,
            label=label,
            due_date=due_date,
            amount=amount,
            payment_type=payment_type,
            sequence=sequence,
            evidence_text="mock: 실제 공고문 납부 일정 추출 전 임시 계산값",
        )


def _mock_checklists(notice: HousingNotice, document: NoticeDocument) -> None:
    EligibilityChecklist.objects.filter(notice=notice, document=document).delete()
    rows = [
        ("residency", "지역 우선공급 확인", f"{notice.region} 및 해당 지역 거주 우선 조건을 공식 공고문에서 확인합니다."),
        ("income", "소득·자산 기준 확인", "공급유형별 소득·자산 기준과 세대 구성 기준을 확인합니다."),
        ("subscription", "청약통장 요건 확인", "가입기간, 납입횟수, 예치금 기준을 확인합니다."),
        ("documents", "제출서류 확인", "주민등록등본, 가족관계증명서, 소득증빙 등 발급 가능 여부를 확인합니다."),
    ]
    for category, title, condition_text in rows:
        EligibilityChecklist.objects.create(
            notice=notice,
            document=document,
            category=category,
            title=title,
            condition_text=condition_text,
            evidence_text="mock: 실제 공고문 근거 문장 추출 전 확인 항목",
            confidence=0.45,
        )


def _area_m2(value: str) -> float:
    match = re.search(r"\\d+(?:\\.\\d+)?", str(value or ""))
    return float(match.group()) if match else 0


def _as_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _area_candidates(base_area: float) -> list[float]:
    common = [49.0, 55.0, 59.0, 74.0, 84.0]
    candidates = [area for area in common if abs(area - base_area) <= 26]
    if not candidates:
        candidates = [base_area]
    if base_area not in candidates:
        candidates.insert(0, base_area)
    return sorted(set(round(area, 2) for area in candidates))


def _price_for_area(base_price: int, base_area: float, area: float) -> int:
    if base_price <= 0 or base_area <= 0:
        return 0
    return round(base_price * (area / base_area))
