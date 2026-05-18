from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.services import find_notice, notices


@api_view(["GET"])
def notice_list(request):
    return Response(notices())


@api_view(["GET"])
def notice_detail(request, notice_id):
    notice = find_notice(notice_id)
    if notice is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(notice)
