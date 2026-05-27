from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import current_notices, find_notice, notices


@api_view(["GET"])
def notice_list(request):
    include_excluded = request.query_params.get("include_excluded") in {"1", "true", "yes"}
    active_only = request.query_params.get("active") in {"1", "true", "yes"}
    source = current_notices if active_only else notices
    return Response(
        source(
            include_excluded=include_excluded,
            region=request.query_params.get("region") or None,
            ownership_type=request.query_params.get("ownership_type") or None,
        )
    )


@api_view(["GET"])
def notice_detail(request, notice_id):
    notice = find_notice(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(notice)
