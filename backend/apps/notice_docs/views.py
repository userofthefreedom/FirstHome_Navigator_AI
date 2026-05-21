from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.notice_docs.models import HousingUnitOption
from apps.notice_docs.serializers import serialize_checklist, serialize_document, serialize_unit_option
from apps.notice_docs.services import analyze_notice_with_mock_data, document_status
from apps.notices.models import HousingNotice


def _notice_or_404(notice_id: int):
    try:
        return HousingNotice.objects.get(id=notice_id)
    except HousingNotice.DoesNotExist:
        return None


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
        }
    )


@api_view(["POST"])
def analyze_notice_document(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    if not notice.is_service_target:
        return Response({"detail": "service target notice is required"}, status=400)

    result = analyze_notice_with_mock_data(notice)
    return Response(
        {
            "notice_id": notice.id,
            "official_document_status": notice.official_document_status,
            "document": serialize_document(result["document"]),
            "unit_options": [serialize_unit_option(option) for option in result["unit_options"]],
            "message": "LLM 연결 전 mock 분석 결과를 생성했습니다.",
        },
        status=201,
    )


@api_view(["GET"])
def notice_unit_options(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)

    options = (
        HousingUnitOption.objects.filter(notice=notice)
        .prefetch_related("payment_schedules")
        .order_by("exclusive_area_m2", "unit_type")
    )
    return Response([serialize_unit_option(option) for option in options])


@api_view(["GET"])
def notice_eligibility_checklists(request, notice_id):
    notice = _notice_or_404(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response([serialize_checklist(item) for item in notice.eligibility_checklists.all()])
