from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import (
    ANALYZE_REQUEST,
    ANALYZE_RESPONSE,
    ASYNC_PARAM,
    CHECKLIST_LIST_RESPONSE,
    CHECKLIST_RESPONSE,
    COMMON_ERROR_RESPONSES,
    DOCUMENT_STATUS_RESPONSE,
    TAGS,
    UNIT_OPTION_LIST_RESPONSE,
    UNIT_OPTION_RESPONSE,
)
from apps.notice_docs.models import HousingUnitOption
from apps.notice_docs.serializers import serialize_checklist, serialize_document, serialize_extraction, serialize_unit_option
from apps.notice_docs.services import analyze_notice_document as run_notice_document_analysis, document_status
from apps.notice_docs.services.analysis import start_notice_document_analysis
from apps.notices.models import HousingNotice


def _notice_or_404(notice_id: int):
    try:
        return HousingNotice.objects.get(id=notice_id)
    except HousingNotice.DoesNotExist:
        return None


@extend_schema(
    tags=[TAGS["notice_docs"]],
    summary="공식 문서 분석 상태",
    description="공고의 공식 PDF 발견/분석 상태, 문서 목록, 최신 추출 결과를 반환합니다.",
    responses={200: DOCUMENT_STATUS_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def notice_document_status(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    status = document_status(notice)
    return Response(
        {
            **{key: value for key, value in status.items() if key != "documents"},
            "documents": [serialize_document(document) for document in status["documents"]],
            "latest_extraction": serialize_extraction(status["latest_extraction"]),
        }
    )


@extend_schema(
    tags=[TAGS["notice_docs"]],
    summary="공식 문서 분석 실행",
    description="공식 공고문 PDF를 발견하고 rule-first 분석과 선택적 LLM 보조 분석을 실행합니다.",
    parameters=[ASYNC_PARAM],
    request=ANALYZE_REQUEST,
    responses={201: ANALYZE_RESPONSE, 202: ANALYZE_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["POST"])
def analyze_notice_document(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    if not notice.is_service_target:
        return Response({"detail": "service target notice is required"}, status=400)

    async_requested = request.query_params.get("async") == "1" or bool(request.data.get("async"))
    if async_requested:
        result = start_notice_document_analysis(notice)
        return Response(
            {
                "notice_id": notice.id,
                "official_document_status": notice.official_document_status,
                "document": serialize_document(result["document"]),
                "analysis_summary": result["analysis_summary"],
                "already_pending": result["already_pending"],
                "message": "공식 문서 분석을 백그라운드 작업으로 시작했습니다. documents/status API로 진행 상태를 확인하세요.",
            },
            status=202,
        )

    result = run_notice_document_analysis(notice)
    return Response(
        {
            "notice_id": notice.id,
            "official_document_status": notice.official_document_status,
            "document": serialize_document(result["document"]),
            "extraction": serialize_extraction(result["extraction"]),
            "unit_options": [serialize_unit_option(option) for option in result["unit_options"]],
            "message": "공식 문서 발견과 분석 파이프라인을 실행했습니다. schema_version과 source로 rules-v1, llm-v1, mock-v1 여부를 확인할 수 있습니다.",
        },
        status=201,
    )


@extend_schema(
    tags=[TAGS["notice_docs"]],
    summary="주택형 옵션 목록",
    description="공식 공고문 분석 결과로 생성된 주택형, 분양가, 융자금, 납부 일정을 반환합니다.",
    responses={200: UNIT_OPTION_LIST_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def notice_unit_options(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)

    options = (
        HousingUnitOption.objects.filter(notice=notice)
        .select_related("extraction")
        .prefetch_related("payment_schedules")
        .order_by("exclusive_area_m2", "unit_type")
    )
    return Response([serialize_unit_option(option) for option in options])


@extend_schema(
    tags=[TAGS["notice_docs"]],
    summary="자격 체크리스트",
    description="공식 공고문에서 추출한 소득, 자산, 무주택, 제출서류 등 확인 항목을 반환합니다.",
    responses={200: CHECKLIST_LIST_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def notice_eligibility_checklists(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response([serialize_checklist(item) for item in notice.eligibility_checklists.all()])
