from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from apps.ai_coach.models import AiExtractionResult
from apps.ai_coach.services.ai_client import AiClientError, chat_completion, llm_enabled
from apps.notice_docs.services.extractors import ExtractedSchedule, ExtractedUnitOption
from apps.notice_docs.services.pdf_parser import PdfPageText
from apps.notice_docs.services.retrieval import candidate_chunks_for_notice_document
from apps.notice_docs.services.schemas import NOTICE_DOCUMENT_EXTRACTION_SCHEMA
from apps.notices.models import HousingNotice


PROMPT_VERSION = "notice-doc-llm-v1"


def extract_notice_document_with_llm(
    *,
    notice: HousingNotice,
    document_id: int,
    pages: list[PdfPageText],
) -> tuple[list[ExtractedUnitOption], list[dict[str, Any]], dict[str, Any]]:
    if not llm_enabled("extraction"):
        return [], [], {"source": "llm_disabled"}

    prompt_input = _prompt_input(notice, pages)
    input_hash = hashlib.sha256(prompt_input.encode("utf-8")).hexdigest()
    log, created = AiExtractionResult.objects.get_or_create(
        source_type="document",
        source_id=document_id,
        extraction_type="housing_notice",
        input_hash=input_hash,
        defaults={
            "source_title": notice.title,
            "source_url": notice.source_url,
            "model_name": "",
            "prompt_version": PROMPT_VERSION,
        },
    )
    if not created and log.status == "succeeded":
        raw_json = log.extracted_data or {}
        options = [_option_from_payload(item) for item in raw_json.get("unit_options", []) if isinstance(item, dict)]
        checklists = _checklists_from_payload(raw_json)
        return options, checklists, {"source": "llm_cache", "input_hash": input_hash, "log_id": log.id}
    if not created:
        log.status = "pending"
        log.error_message = ""
        log.save(update_fields=["status", "error_message", "updated_at"])

    try:
        response = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 한국 공공분양 입주자모집공고 PDF를 구조화하는 추출기다. "
                        "원문에 없는 값은 0 또는 빈 문자열로 둔다. 금액은 반드시 원 단위 정수로 변환한다. "
                        "확정 판정이 아니라 공고문 확인 항목만 추출한다."
                    ),
                },
                {"role": "user", "content": prompt_input},
            ],
            response_schema=NOTICE_DOCUMENT_EXTRACTION_SCHEMA,
            temperature=0.1,
        )
    except AiClientError as exc:
        log.mark_failed(str(exc))
        return [], [], {"source": "llm_failed", "error": str(exc)}

    raw_json = response.parsed_json or {}
    options = [_option_from_payload(item) for item in raw_json.get("unit_options", []) if isinstance(item, dict)]
    checklists = _checklists_from_payload(raw_json)
    log.model_name = response.model
    log.mark_succeeded(
        extracted_data=raw_json,
        confidence={"overall": _average_confidence(options)},
        warnings=[str(item) for item in raw_json.get("warnings", [])],
        raw_response=response.raw_response,
    )
    return options, checklists, {"source": "llm", "input_hash": input_hash, "log_id": log.id}


def _checklists_from_payload(raw_json: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "category": str(item.get("category", "other")),
            "title": str(item.get("title", "공식 확인 항목")),
            "condition_text": str(item.get("condition_text", "")),
            "evidence_text": str(item.get("evidence_text", "")),
            "confidence": float(item.get("confidence") or 0),
        }
        for item in raw_json.get("eligibility_checklists", [])
        if isinstance(item, dict)
    ]


def _prompt_input(notice: HousingNotice, pages: list[PdfPageText]) -> str:
    chunks = _candidate_chunks(pages)
    return (
        f"공고명: {notice.title}\n"
        f"지역: {notice.region} {notice.district}\n"
        f"공급유형: {notice.supply_type} / {notice.housing_type}\n\n"
        "아래 공고문 후보 페이지에서 주택형 옵션, 납부 일정, 공식 확인 체크리스트를 JSON으로 추출하세요.\n\n"
        + "\n\n".join(chunks)
    )


def _candidate_chunks(pages: list[PdfPageText], *, limit: int = 8, max_chars: int = 1800) -> list[str]:
    return candidate_chunks_for_notice_document(pages, limit_per_purpose=max(1, limit // 3), max_chars=max_chars)[:limit]


def _option_from_payload(item: dict[str, Any]) -> ExtractedUnitOption:
    schedules = [
        ExtractedSchedule(
            label=str(schedule.get("label", "")),
            due_date=_parse_date(schedule.get("due_date")),
            amount=max(0, int(schedule.get("amount") or 0)),
            payment_type=str(schedule.get("payment_type") or "other"),
            sequence=max(0, int(schedule.get("sequence") or 0)),
            evidence_text=str(schedule.get("evidence_text", "")),
        )
        for schedule in item.get("payment_schedules", [])
        if isinstance(schedule, dict)
    ]
    evidence = [
        {
            "field_path": str(row.get("field_path", "")),
            "page_no": int(row.get("page_no") or 0),
            "source_text": str(row.get("source_text", "")),
            "confidence": float(row.get("confidence") or 0),
        }
        for row in item.get("evidence", [])
        if isinstance(row, dict)
    ]
    return ExtractedUnitOption(
        unit_type=str(item.get("unit_type", "")),
        exclusive_area_m2=float(item.get("exclusive_area_m2") or 0),
        floor_group=str(item.get("floor_group", "")),
        option_type=str(item.get("option_type") or "basic"),
        base_price=max(0, int(item.get("base_price") or 0)),
        loan_amount=max(0, int(item.get("loan_amount") or 0)),
        balcony_extension_price=max(0, int(item.get("balcony_extension_price") or 0)),
        confidence=float(item.get("confidence") or 0),
        source_page=int(item.get("source_page") or 0),
        source_text=str(item.get("source_text", "")),
        payment_schedules=schedules,
        evidence=evidence,
    )


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _average_confidence(options: list[ExtractedUnitOption]) -> float:
    if not options:
        return 0
    return round(sum(option.confidence for option in options) / len(options), 2)
