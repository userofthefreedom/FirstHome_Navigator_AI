from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any

from apps.ai_coach.models import AiExtractionResult
from apps.ai_coach.services.ai_client import AiClientError, chat_completion, llm_enabled
from apps.notice_docs.services.extractors import ExtractedSchedule, ExtractedUnitOption
from apps.notice_docs.services.pdf_parser import PdfPageText
from apps.notice_docs.services.retrieval import candidate_chunks_for_notice_document
from apps.notice_docs.services.schemas import NOTICE_DOCUMENT_EXTRACTION_SCHEMA
from apps.notices.models import HousingNotice


PROMPT_VERSION = "notice-doc-llm-v2"
ALLOWED_OPTION_TYPES = {"basic", "general_supply", "pre_subscription", "minus", "other"}
OPTION_TYPE_ALIASES = {
    "general": "general_supply",
    "general_sale": "general_supply",
    "main": "general_supply",
    "standard": "general_supply",
    "pre": "pre_subscription",
    "prior_subscription": "pre_subscription",
    "advance": "pre_subscription",
    "minus_option": "minus",
}


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
        options = [_option_from_payload(item, notice=notice) for item in raw_json.get("unit_options", []) if isinstance(item, dict)]
        checklists = _checklists_from_payload(raw_json)
        return options, checklists, {
            "source": "llm_cache",
            "input_hash": input_hash,
            "log_id": log.id,
            "required_documents": _required_documents_from_payload(raw_json),
            "warnings": [str(item) for item in raw_json.get("warnings", [])],
        }
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
                        "공고문에 없는 값은 추정하지 말고 0 또는 빈 문자열로 둔다. "
                        "금액은 모두 원 단위 정수로 변환한다. "
                        "융자금은 분양가에 포함된 주택도시기금 등 대출성 금액이며, 계약금/중도금/잔금과 구분한다."
                    ),
                },
                {"role": "user", "content": prompt_input},
            ],
            response_schema=NOTICE_DOCUMENT_EXTRACTION_SCHEMA,
            temperature=0.1,
        )
    except AiClientError as exc:
        log.mark_failed(str(exc))
        stale_options, stale_checklists = _latest_successful_cached_result(document_id, exclude_input_hash=input_hash, notice=notice)
        if stale_options:
            raw_json = (
                AiExtractionResult.objects.filter(
                    source_type="document",
                    source_id=document_id,
                    extraction_type="housing_notice",
                    status="succeeded",
                )
                .exclude(input_hash=input_hash)
                .order_by("-updated_at", "-id")
                .values_list("extracted_data", flat=True)
                .first()
                or {}
            )
            return stale_options, stale_checklists, {
                "source": "llm_stale_cache",
                "input_hash": input_hash,
                "log_id": log.id,
                "fallback_reason": str(exc),
                "required_documents": _required_documents_from_payload(raw_json),
                "warnings": [str(item) for item in raw_json.get("warnings", [])] if isinstance(raw_json, dict) else [],
            }
        return [], [], {"source": "llm_failed", "error": str(exc)}

    raw_json = response.parsed_json or {}
    options = [_option_from_payload(item, notice=notice) for item in raw_json.get("unit_options", []) if isinstance(item, dict)]
    checklists = _checklists_from_payload(raw_json)
    log.model_name = response.model
    log.mark_succeeded(
        extracted_data=raw_json,
        confidence={"overall": _average_confidence(options)},
        warnings=[str(item) for item in raw_json.get("warnings", [])],
        raw_response=response.raw_response,
    )
    return options, checklists, {
        "source": "llm",
        "input_hash": input_hash,
        "log_id": log.id,
        "required_documents": _required_documents_from_payload(raw_json),
        "warnings": [str(item) for item in raw_json.get("warnings", [])],
    }


def _checklists_from_payload(raw_json: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "category": str(item.get("category", "other")),
            "title": str(item.get("title", "공식 확인 항목")),
            "condition_text": str(item.get("condition_text", "")),
            "evidence_text": str(item.get("evidence_text", "")),
            "page_no": max(0, int(item.get("page_no") or 0)),
            "confidence": float(item.get("confidence") or 0),
        }
        for item in raw_json.get("eligibility_checklists", [])
        if isinstance(item, dict)
    ]


def _required_documents_from_payload(raw_json: dict[str, Any]) -> list[str]:
    documents: list[str] = []
    seen: set[str] = set()
    for item in raw_json.get("required_documents", []):
        label = re.sub(r"\s+", " ", str(item or "")).strip()
        key = re.sub(r"\s+", "", label).casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        documents.append(label)
    return documents[:18]


def _latest_successful_cached_result(
    document_id: int,
    *,
    exclude_input_hash: str,
    notice: HousingNotice,
) -> tuple[list[ExtractedUnitOption], list[dict[str, Any]]]:
    cached_log = (
        AiExtractionResult.objects.filter(
            source_type="document",
            source_id=document_id,
            extraction_type="housing_notice",
            status="succeeded",
        )
        .exclude(input_hash=exclude_input_hash)
        .order_by("-updated_at", "-id")
        .first()
    )
    if cached_log is None:
        return [], []

    raw_json = cached_log.extracted_data or {}
    options = [_option_from_payload(item, notice=notice) for item in raw_json.get("unit_options", []) if isinstance(item, dict)]
    checklists = _checklists_from_payload(raw_json)
    return options, checklists


def _prompt_input(notice: HousingNotice, pages: list[PdfPageText]) -> str:
    chunks = _candidate_chunks(pages)
    return (
        f"공고명: {notice.title}\n"
        f"지역: {notice.region} {notice.district}\n"
        f"공급유형: {notice.supply_type} / {notice.housing_type}\n\n"
        "아래 공고문 후보 페이지에서 주택형 옵션, 납부 일정, 공식 확인 체크리스트를 JSON으로 추출하세요.\n"
        "- option_type은 다음 중 하나만 사용합니다.\n"
        "  basic: 유형 구분이 명확하지 않은 기본 분양가 표\n"
        "  general_supply: 본청약, 일반공급, 특별공급 등 일반적인 납부안\n"
        "  pre_subscription: 사전청약 당첨자 납부안\n"
        "  minus: 마이너스 옵션\n"
        "  other: 위 분류로 확정하기 어려운 경우\n"
        "- 같은 주택형/층이라도 본청약과 사전청약 납부안이 나뉘면 별도 unit_option으로 추출합니다.\n"
        "- loan_amount는 융자금/주택도시기금처럼 분양가에 포함된 대출성 금액입니다.\n"
        "- payment_schedules에는 계약금, 중도금, 잔금, 할부금/납부유예금 등 실제 납부 일정만 넣습니다.\n"
        "- 융자금은 payment_schedules에 넣지 말고 반드시 loan_amount에만 기록합니다.\n"
        "- eligibility_checklists는 출처 page_no와 근거 문장을 함께 기록합니다.\n"
        "- required_documents에는 당첨자 제출서류와 계약 구비서류를 짧은 서류명 배열로 기록합니다.\n\n"
        + "\n\n".join(chunks)
    )


def _candidate_chunks(pages: list[PdfPageText], *, limit: int = 8, max_chars: int = 1800) -> list[str]:
    return candidate_chunks_for_notice_document(pages, limit_per_purpose=max(1, limit // 3), max_chars=max_chars)[:limit]


def _option_from_payload(item: dict[str, Any], *, notice: HousingNotice | None = None) -> ExtractedUnitOption:
    schedules, loan_amount_from_schedules = _schedules_from_payload(item.get("payment_schedules", []))
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
    unit_type = str(item.get("unit_type", "")).strip()
    exclusive_area_m2 = _exclusive_area_from_payload(item, unit_type, notice)
    return ExtractedUnitOption(
        unit_type=unit_type,
        exclusive_area_m2=exclusive_area_m2,
        floor_group=str(item.get("floor_group", "")),
        option_type=_option_type_from_payload(item),
        base_price=max(0, int(item.get("base_price") or 0)),
        loan_amount=max(max(0, int(item.get("loan_amount") or 0)), loan_amount_from_schedules),
        balcony_extension_price=max(0, int(item.get("balcony_extension_price") or 0)),
        confidence=float(item.get("confidence") or 0),
        source_page=int(item.get("source_page") or 0),
        source_text=str(item.get("source_text", "")),
        payment_schedules=schedules,
        evidence=evidence,
    )


def _schedules_from_payload(raw_schedules: Any) -> tuple[list[ExtractedSchedule], int]:
    schedules: list[ExtractedSchedule] = []
    loan_amount = 0
    for schedule in raw_schedules if isinstance(raw_schedules, list) else []:
        if not isinstance(schedule, dict):
            continue
        amount = max(0, int(schedule.get("amount") or 0))
        payment_type = str(schedule.get("payment_type") or "other").strip()
        if payment_type == "loan":
            loan_amount = max(loan_amount, amount)
            continue
        schedules.append(
            ExtractedSchedule(
                label=str(schedule.get("label", "")),
                due_date=_parse_date(schedule.get("due_date")),
                amount=amount,
                payment_type=payment_type,
                sequence=max(0, int(schedule.get("sequence") or 0)),
                evidence_text=str(schedule.get("evidence_text", "")),
            )
        )
    return schedules, loan_amount


def _option_type_from_payload(item: dict[str, Any]) -> str:
    raw_type = str(item.get("option_type") or "").strip().casefold()
    normalized = OPTION_TYPE_ALIASES.get(raw_type, raw_type)
    if normalized in ALLOWED_OPTION_TYPES:
        return normalized

    text = " ".join(str(item.get(key) or "") for key in ("floor_group", "source_text"))
    if "사전청약" in text or "계약금(5%)" in text or "계약금 5%" in text:
        return "pre_subscription"
    if "본청약" in text or "일반공급" in text or "특별공급" in text or "계약금(10%)" in text or "계약금 10%" in text:
        return "general_supply"
    if "마이너스" in text:
        return "minus"
    return "basic"


def _exclusive_area_from_payload(item: dict[str, Any], unit_type: str, notice: HousingNotice | None) -> float:
    explicit_area = _safe_float(item.get("exclusive_area_m2"))
    if explicit_area > 0:
        return explicit_area

    supply_area = _exclusive_area_from_supply_summary(unit_type, notice)
    if supply_area > 0:
        return supply_area

    match = re.search(r"(\d{2,3})(?:\.(\d{1,4}))?", unit_type)
    if not match:
        return 0
    integer_part = match.group(1).lstrip("0") or "0"
    decimal_part = (match.group(2) or "").rstrip("0")
    number_text = integer_part if not decimal_part else f"{integer_part}.{decimal_part}"
    return round(_safe_float(number_text), 2)


def _exclusive_area_from_supply_summary(unit_type: str, notice: HousingNotice | None) -> float:
    if notice is None:
        return 0
    supply_summary = (notice.source_meta or {}).get("supply_summary") or {}
    unit_options = supply_summary.get("unit_options") or []
    normalized_target = _normalize_unit_key(unit_type)
    for option in unit_options:
        if not isinstance(option, dict):
            continue
        candidates = [option.get("raw_unit_type"), option.get("unit_type")]
        if any(_normalize_unit_key(candidate) == normalized_target for candidate in candidates):
            area = _safe_float(option.get("exclusive_area_m2"))
            if area > 0:
                return area
    return 0


def _normalize_unit_key(value: Any) -> str:
    text = str(value or "").upper().strip()
    match = re.match(r"0*(\d{2,3})(?:\.\d+)?\s*([A-Z]?)", text)
    if not match:
        return re.sub(r"\s+", "", text)
    return f"{int(match.group(1))}{match.group(2)}"


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


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
