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
    review_issues = _review_issues(latest_extraction, latest_error)

    if not is_service_target:
        stage = "excluded"
        label = "서비스 제외"
        tone = "muted"
        next_action = "소유형 공공분양 준비 범위 밖의 공고입니다."
    elif is_mock:
        stage = "mock"
        label = "임시 추정"
        tone = "warning"
        next_action = "공식 PDF 분석을 다시 실행해 근거 문장 기반 결과로 교체하세요."
    elif official_status == "analyzed" and unit_option_count > 0 and extraction_status == "needs_review":
        stage = "needs_review"
        label = "근거 검토 필요"
        tone = "warning"
        next_action = review_issues[0]["message"] if review_issues else "추출 금액과 일정의 원문 근거를 확인하세요."
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
        next_action = "공식 문서 분석을 진행 중입니다."
    elif document_count > 0:
        stage = "discovered"
        label = "문서 발견"
        tone = "info"
        next_action = "PDF 분석을 실행해 주택형 옵션을 추출하세요."
    else:
        stage = "not_requested"
        label = "분석 필요"
        tone = "muted"
        next_action = "공식 문서 발견과 PDF 분석을 실행하세요."

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
        "review_issues": review_issues,
    }


def fixture_analysis_summary(notice: dict[str, Any] | Any) -> dict[str, Any]:
    getter = notice.get if isinstance(notice, dict) else lambda key, default=None: getattr(notice, key, default)
    is_service_target = bool(getter("is_service_target", False))
    official_status = getter("official_document_status", "not_requested")
    document_count = int(getter("document_count", 0) or 0)
    unit_option_count = int(getter("unit_option_count", 0) or 0)

    if not is_service_target:
        stage, label, tone, next_action = ("excluded", "서비스 제외", "muted", "소유형 공공분양 준비 범위 밖의 공고입니다.")
    elif official_status == "analyzed" and unit_option_count > 0:
        stage, label, tone, next_action = ("verified", "공식 분석 완료", "success", "주택형 옵션과 자금 일정을 비교할 수 있습니다.")
    elif official_status == "failed":
        stage, label, tone, next_action = ("failed", "분석 실패", "danger", "공식 PDF 발견 또는 추출 조건을 확인하세요.")
    elif official_status == "pending":
        stage, label, tone, next_action = ("pending", "분석 중", "info", "공식 문서 분석을 진행 중입니다.")
    elif document_count > 0:
        stage, label, tone, next_action = ("discovered", "문서 발견", "info", "PDF 분석을 실행해 주택형 옵션을 추출하세요.")
    else:
        stage, label, tone, next_action = ("not_requested", "분석 필요", "muted", "공식 문서 발견과 PDF 분석을 실행하세요.")

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
        "review_issues": [],
    }


def _extraction_source(extraction: Any) -> str:
    if extraction is None or not isinstance(getattr(extraction, "raw_json", None), dict):
        return ""
    return str(extraction.raw_json.get("source", ""))


def _review_issues(extraction: Any, latest_error: str = "") -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    raw_json = getattr(extraction, "raw_json", None)
    if extraction is not None and float(getattr(extraction, "confidence", 1) or 0) < 0.6:
        issues.append(
            {
                "code": "low_confidence",
                "title": "낮은 추출 신뢰도",
                "message": "공고문 추출 신뢰도가 낮아 금액과 일정의 원문 대조가 필요합니다.",
                "target": "extraction",
                "severity": "warning",
                "action": "공급금액 표와 납부일정 표를 원문에서 다시 확인하세요.",
            }
        )
    if isinstance(raw_json, dict):
        for issue in raw_json.get("review_issues", []) or []:
            if isinstance(issue, dict) and issue.get("code"):
                issues.append(
                    {
                        "code": str(issue.get("code")),
                        "title": str(issue.get("title") or "분석 확인 필요"),
                        "message": str(issue.get("message") or "공고문 원문 확인이 필요합니다."),
                        "target": str(issue.get("target") or "extraction"),
                        "severity": str(issue.get("severity") or "warning"),
                        "action": str(issue.get("action") or _default_issue_action(str(issue.get("code") or ""))),
                    }
                )
        for warning in raw_json.get("warnings", []) if isinstance(raw_json.get("warnings"), list) else []:
            issue = _issue_from_warning(str(warning), "extraction")
            if issue:
                issues.append(issue)
        if raw_json.get("source") in {"llm_failed", "llm_stale_cache"}:
            issues.append(
                {
                    "code": "llm_fallback",
                    "title": "LLM 보조 추출 확인 필요",
                    "message": "LLM 보조 추출이 실패했거나 이전 캐시를 사용했습니다.",
                    "target": "llm",
                    "severity": "warning",
                    "action": "규칙 기반 추출 결과와 공식 원문을 우선 비교하세요.",
                }
            )
        extraction_status = str(getattr(extraction, "status", "") or raw_json.get("status") or "")
        if extraction_status == "needs_review" and not raw_json.get("required_documents"):
            issues.append(
                {
                    "code": "required_documents_missing",
                    "title": "필수서류 추출 부족",
                    "message": "당첨자 제출서류와 계약 구비서류가 충분히 추출되지 않았습니다.",
                    "target": "required_documents",
                    "severity": "warning",
                    "action": "공고문 제출서류/구비서류 표를 직접 확인하세요.",
                }
            )
    warnings = raw_json.get("warnings", {}) if isinstance(raw_json, dict) else {}
    if isinstance(warnings, dict):
        for option_key, option_warnings in warnings.items():
            for warning in option_warnings if isinstance(option_warnings, list) else [option_warnings]:
                issue = _issue_from_warning(str(warning), str(option_key))
                if issue:
                    issues.append(issue)
    if latest_error:
        issues.append(
            {
                "code": "document_error",
                "title": "문서 분석 오류",
                "message": latest_error,
                "target": "document",
                "severity": "danger",
                "action": "공식 PDF URL과 파일 형식을 확인한 뒤 다시 분석하세요.",
            }
        )
    return _dedupe_issues(issues)[:5]


def _issue_from_warning(warning: str, target: str) -> dict[str, Any] | None:
    if not warning:
        return None
    if "합계" in warning or "차이" in warning:
        code, title, message = (
            "amount_mismatch",
            "금액 합계 검토",
            f"{target} 옵션의 계약금·중도금·잔금 합계와 분양가 차이가 큽니다.",
        )
    elif "납부 일정" in warning:
        code, title, message = ("schedule_missing", "납부 일정 누락", f"{target} 옵션의 납부 일정 원문을 확인해야 합니다.")
    elif "근거 문장" in warning:
        code, title, message = ("source_missing", "근거 문장 부족", f"{target} 옵션의 공고문 근거 문장이 부족합니다.")
    elif "분양가" in warning:
        code, title, message = ("price_missing", "분양가 확인 필요", f"{target} 옵션의 분양가를 확인할 수 없습니다.")
    else:
        code, title, message = ("validation_warning", "분석 경고", f"{target}: {warning}")
    return {
        "code": code,
        "title": title,
        "message": message,
        "target": target,
        "severity": "warning",
        "action": _default_issue_action(code),
    }


def _default_issue_action(code: str) -> str:
    actions = {
        "amount_mismatch": "분양가와 계약금·중도금·잔금·융자금 합계를 원문 표에서 대조하세요.",
        "schedule_missing": "납부일정 표의 회차와 예정일을 공식 공고문에서 확인하세요.",
        "source_missing": "해당 항목의 공고문 페이지와 근거 문장을 다시 확인하세요.",
        "price_missing": "주택형별 공급금액 표를 기준으로 분양가를 확인하세요.",
        "validation_warning": "분석 결과와 공식 원문이 다른지 확인하세요.",
        "required_documents_missing": "제출서류/구비서류 표를 공식 공고문에서 확인하세요.",
    }
    return actions.get(code, "공식 공고문 원문과 화면의 분석 결과를 비교하세요.")


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue["code"], issue["target"])
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result
