from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.services import coach_summary, default_profile


@api_view(["POST"])
def coach_summary_view(request):
    notice_id = int(request.data.get("notice_id", 101))
    profile = default_profile()
    profile.update(request.data.get("profile", {}))
    summary = coach_summary(notice_id, profile)
    if summary is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(summary)
