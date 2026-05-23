from __future__ import annotations

from typing import Any

from django.db import OperationalError, ProgrammingError


def notice_analysis_summary(notice: Any) -> dict[str, Any]:
    try:
        documents = notice.documents.all()
        unit_options = notice.unit_options.all()
        latest_extraction = notice.extractions.order_by("-created_at", "-id").first()
        document_count = documents.count()
        unit_option_count = unit_options.count()
        latest_document = documents.order_by("-updated_at", "-id").first()
    except (AttributeError, OperationalError, ProgrammingError):
        return fixture_analysis_summary(notice)

    source = _extraction_source(latest_extraction)
    schema_version = getattr(latest_extraction, "schema_version", "") if latest_extraction else ""
    extraction_status = getattr(latest_extraction, "status", "") if latest_extraction else ""
    is_mock = schema_version == "mock-v1" or extraction_status == "mock" or source == "mock"
    official_status = getattr(notice, "official_document_status", "not_requested")
    is_service_target = bool(getattr(notice, "is_service_target", False))
    latest_error = getattr(latest_document, "error_message", "") if latest_document else ""
    latest_document_status = getattr(latest_document, "status", "") if latest_document else ""

    if not is_service_target:
        stage = "excluded"
        label = "서비스 제외"
        tone = "muted"
        next_action = "공공분양 전용 범위 밖의 공고입니다."
    elif is_mock:
        stage = "mock"
        label = "임시 추정"
        tone = "warning"
        next_action = "공식 PDF 분석을 다시 실행해 근거 문장으로 대체하세요."
    elif official_status == "analyzed" and unit_option_count > 0 and extraction_status == "needs_review":
        stage = "needs_review"
        label = "근거 검토 필요"
        tone = "warning"
        next_action = "추출된 금액과 일정의 원문 근거를 확인하세요."
    elif official_status == "analyzed" and unit_option_count > 0:
        stage = "verified"
        label = "공식 분석 완료"
        tone = "success"
        next_action = "주택형 옵션과 자금 일정을 비교할 수 있습니다."
    elif official_status == "failed" or latest_document_status == "failed":
        stage = "failed"
        label = "분석 실패"
        tone = "danger"
        next_action = latest_error or "공식 PDF 발견 또는 추출 조건을 확인하세요."
    elif official_status == "pending" or latest_document_status == "pending":
        stage = "pending"
        label = "분석 중"
        tone = "info"
        next_action = "분석 요청이 진행 중입니다."
    elif document_count > 0:
        stage = "discovered"
        label = "문서 발견"
        tone = "info"
        next_action = "PDF 분석을 실행해 주택형 옵션을 추출하세요."
    else:
        stage = "not_requested"
        label = "분석 필요"
        tone = "muted"
        next_action = "공식 문서 discovery와 PDF 분석을 실행하세요."

    return {
        "stage": stage,
        "label": label,
        "tone": tone,
        "next_action": next_action,
        "is_mock": is_mock,
        "source": source,
        "schema_version": schema_version,
        "extraction_status": extraction_status,
        "document_status": latest_document_status,
        "document_count": document_count,
        "unit_option_count": unit_option_count,
        "latest_error": latest_error,
    }


def fixture_analysis_summary(notice: dict[str, Any] | Any) -> dict[str, Any]:
    getter = notice.get if isinstance(notice, dict) else lambda key, default=None: getattr(notice, key, default)
    is_service_target = bool(getter("is_service_target", False))
    official_status = getter("official_document_status", "not_requested")
    document_count = int(getter("document_count", 0) or 0)
    unit_option_count = int(getter("unit_option_count", 0) or 0)

    if not is_service_target:
        stage, label, tone, next_action = ("excluded", "서비스 제외", "muted", "공공분양 전용 범위 밖의 공고입니다.")
    elif official_status == "analyzed" and unit_option_count > 0:
        stage, label, tone, next_action = ("verified", "공식 분석 완료", "success", "주택형 옵션과 자금 일정을 비교할 수 있습니다.")
    elif official_status == "failed":
        stage, label, tone, next_action = ("failed", "분석 실패", "danger", "공식 PDF 발견 또는 추출 조건을 확인하세요.")
    elif official_status == "pending":
        stage, label, tone, next_action = ("pending", "분석 중", "info", "분석 요청이 진행 중입니다.")
    elif document_count > 0:
        stage, label, tone, next_action = ("discovered", "문서 발견", "info", "PDF 분석을 실행해 주택형 옵션을 추출하세요.")
    else:
        stage, label, tone, next_action = ("not_requested", "분석 필요", "muted", "공식 문서 discovery와 PDF 분석을 실행하세요.")

    return {
        "stage": stage,
        "label": label,
        "tone": tone,
        "next_action": next_action,
        "is_mock": False,
        "source": "",
        "schema_version": "",
        "extraction_status": "",
        "document_status": "",
        "document_count": document_count,
        "unit_option_count": unit_option_count,
        "latest_error": "",
    }


def _extraction_source(extraction: Any) -> str:
    if extraction is None or not isinstance(getattr(extraction, "raw_json", None), dict):
        return ""
    return str(extraction.raw_json.get("source", ""))
