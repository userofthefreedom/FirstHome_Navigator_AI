from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from django.utils import timezone

from apps.notice_docs.models import (
    EligibilityChecklist,
    ExtractionEvidence,
    HousingUnitOption,
    NoticeDocument,
    NoticeExtraction,
    PaymentSchedule,
)
from apps.notice_docs.services.discovery_lh import discover_documents_for_notice
from apps.notice_docs.services.extractors import ExtractedUnitOption, extract_checklist_items, extract_unit_options_from_pages
from apps.notice_docs.services.llm_extractors import extract_notice_document_with_llm
from apps.notice_docs.services.pdf_parser import PdfParserUnavailable, parse_pdf_text, resolve_local_pdf_path
from apps.notice_docs.services.validators import extraction_confidence, extraction_status, validate_unit_options
from apps.notices.models import HousingNotice


def analyze_notice_document(notice: HousingNotice, *, pdf_path: str | Path | None = None) -> dict[str, Any]:
    previous_result = _latest_analyzed_result(notice)
    documents = discover_documents_for_notice(notice)
    document = _select_document(notice, documents)
    document.status = "pending"
    document.error_message = ""
    document.save(update_fields=["status", "error_message", "updated_at"])

    local_pdf_path = Path(pdf_path) if pdf_path else _local_pdf_for_document(document)
    if local_pdf_path:
        try:
            parsed_pages = parse_pdf_text(local_pdf_path)
        except (PdfParserUnavailable, OSError, ValueError) as exc:
            return _analysis_failed_with_preserved_result(notice, document, str(exc), previous_result)

        extracted_options = validate_unit_options(extract_unit_options_from_pages(parsed_pages))
        checklist_items = extract_checklist_items(parsed_pages)
        source_meta: dict[str, Any] = {"source": "rules"}
        if not extracted_options or any(option.validation_warnings for option in extracted_options):
            llm_options, llm_checklists, llm_meta = extract_notice_document_with_llm(
                notice=notice,
                document_id=document.id,
                pages=parsed_pages,
            )
            if llm_options:
                extracted_options = validate_unit_options(llm_options)
                checklist_items = llm_checklists or checklist_items
                source_meta = llm_meta
        if extracted_options:
            return _save_extraction_result(
                notice,
                document,
                extracted_options,
                checklist_items,
                local_pdf_path,
                source_meta=source_meta,
            )

    return _analysis_failed_with_preserved_result(
        notice,
        document,
        "분석 가능한 로컬 PDF가 없거나 주택형 표를 찾지 못했습니다.",
        previous_result,
    )


def analyze_notice_with_mock_data(notice: HousingNotice) -> dict[str, Any]:
    return _create_mock_analysis(notice, _document_for_notice(notice), reason="LLM 연결 전 샘플 추출 데이터")


def document_status(notice: HousingNotice) -> dict[str, Any]:
    documents = list(notice.documents.order_by("-updated_at", "-id"))
    unit_options = HousingUnitOption.objects.filter(notice=notice)
    latest_extraction = notice.extractions.order_by("-created_at", "-id").first()
    return {
        "notice_id": notice.id,
        "official_document_status": notice.official_document_status,
        "document_count": len(documents),
        "unit_option_count": unit_options.count(),
        "analyzed_option_count": unit_options.filter(confidence__gt=0).count(),
        "documents": documents,
        "latest_extraction": latest_extraction,
    }


def _save_extraction_result(
    notice: HousingNotice,
    document: NoticeDocument,
    extracted_options: list[ExtractedUnitOption],
    checklist_items: list[dict[str, Any]],
    pdf_path: Path,
    *,
    source_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = extraction_status(extracted_options)
    source_meta = source_meta or {"source": "rules"}
    schema_version = "llm-v1" if str(source_meta.get("source", "")).startswith("llm") else "rules-v1"
    extraction = NoticeExtraction.objects.create(
        notice=notice,
        document=document,
        schema_version=schema_version,
        status=status,
        confidence=extraction_confidence(extracted_options),
        raw_json={
            **source_meta,
            "pdf_path": str(pdf_path),
            "option_count": len(extracted_options),
            "status": status,
            "warnings": {
                option.unit_type: option.validation_warnings
                for option in extracted_options
                if option.validation_warnings
            },
        },
    )

    HousingUnitOption.objects.filter(notice=notice).delete()
    options = [_save_unit_option(notice, document, extraction, option) for option in extracted_options]
    _save_checklists(notice, document, checklist_items)

    document.status = "analyzed" if status in {"valid", "needs_review"} else "failed"
    document.analyzed_at = timezone.now()
    document.error_message = "" if document.status == "analyzed" else "PDF 추출 결과 검증 실패"
    document.save(update_fields=["status", "analyzed_at", "error_message", "updated_at"])

    notice.official_document_status = "analyzed" if document.status == "analyzed" else "failed"
    notice.save(update_fields=["official_document_status", "updated_at"])
    return {"document": document, "extraction": extraction, "unit_options": options}


def _save_unit_option(
    notice: HousingNotice,
    document: NoticeDocument,
    extraction: NoticeExtraction,
    extracted: ExtractedUnitOption,
) -> HousingUnitOption:
    option, _created = HousingUnitOption.objects.update_or_create(
        notice=notice,
        unit_type=extracted.unit_type,
        floor_group=extracted.floor_group,
        option_type=extracted.option_type,
        defaults={
            "document": document,
            "extraction": extraction,
            "exclusive_area_m2": extracted.exclusive_area_m2,
            "base_price": extracted.base_price,
            "loan_amount": extracted.loan_amount,
            "balcony_extension_price": extracted.balcony_extension_price,
            "confidence": extracted.confidence,
            "source_page": extracted.source_page,
            "source_text": extracted.source_text,
        },
    )
    option.payment_schedules.all().delete()
    for schedule in extracted.payment_schedules:
        PaymentSchedule.objects.create(
            unit_option=option,
            label=schedule.label,
            due_date=schedule.due_date,
            amount=schedule.amount,
            payment_type=schedule.payment_type,
            sequence=schedule.sequence,
            evidence_text=schedule.evidence_text,
        )
    for evidence in extracted.evidence:
        ExtractionEvidence.objects.create(
            extraction=extraction,
            field_path=evidence["field_path"],
            page_no=evidence["page_no"],
            source_text=evidence["source_text"],
            confidence=evidence["confidence"],
        )
    return option


def _save_checklists(notice: HousingNotice, document: NoticeDocument, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    EligibilityChecklist.objects.filter(notice=notice, document=document).delete()
    for row in rows:
        EligibilityChecklist.objects.create(
            notice=notice,
            document=document,
            category=row["category"],
            title=row["title"],
            condition_text=row["condition_text"],
            evidence_text=row["evidence_text"],
            confidence=row["confidence"],
        )


def _analysis_failed_with_preserved_result(
    notice: HousingNotice,
    document: NoticeDocument,
    reason: str,
    previous_result: dict[str, Any] | None,
) -> dict[str, Any]:
    document.status = "failed"
    document.error_message = reason[:240]
    document.save(update_fields=["status", "error_message", "updated_at"])
    if previous_result:
        notice.official_document_status = "analyzed"
        notice.save(update_fields=["official_document_status", "updated_at"])
        return previous_result
    return _create_mock_analysis(notice, document, reason=reason)


def _latest_analyzed_result(notice: HousingNotice) -> dict[str, Any] | None:
    options = list(
        HousingUnitOption.objects.filter(notice=notice)
        .select_related("document", "extraction")
        .prefetch_related("payment_schedules")
        .order_by("exclusive_area_m2", "id")
    )
    if not options:
        return None
    document = next((option.document for option in options if option.document_id), None)
    extraction = next((option.extraction for option in options if option.extraction_id), None)
    if document is None:
        document = notice.documents.order_by("-updated_at", "-id").first()
    if document is None or extraction is None:
        return None
    return {"document": document, "extraction": extraction, "unit_options": options}


def _create_mock_analysis(notice: HousingNotice, document: NoticeDocument, *, reason: str) -> dict[str, Any]:
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
            "reason": reason,
            "notice_id": notice.id,
        },
    )

    options = _mock_unit_options(notice, document, extraction)
    _mock_checklists(notice, document)
    extraction.raw_json = {**extraction.raw_json, "option_count": len(options)}
    extraction.save(update_fields=["raw_json"])

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


def _select_document(notice: HousingNotice, documents: list[NoticeDocument]) -> NoticeDocument:
    pdf_documents = [document for document in documents if document.file_name.lower().endswith(".pdf")]
    if pdf_documents:
        return pdf_documents[0]
    if documents:
        return documents[0]
    return _document_for_notice(notice)


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


def _local_pdf_for_document(document: NoticeDocument) -> Path | None:
    return (
        resolve_local_pdf_path(document.document_url)
        or resolve_local_pdf_path(document.source_url)
        or resolve_local_pdf_path(document.file_name)
    )


def _document_name(notice: HousingNotice) -> str:
    title = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", notice.title).strip("_")
    return f"{title[:80]}_mock.pdf" if title else "official_notice_mock.pdf"


def _mock_unit_options(
    notice: HousingNotice,
    document: NoticeDocument,
    extraction: NoticeExtraction,
) -> list[HousingUnitOption]:
    HousingUnitOption.objects.filter(notice=notice).delete()
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
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else 0


def _as_date(value: Any) -> date | None:
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
