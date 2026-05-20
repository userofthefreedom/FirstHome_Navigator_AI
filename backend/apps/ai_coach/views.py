from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.profiles.services import profile_from_request
from apps.services import coach_summary


@api_view(["POST"])
def coach_summary_view(request):
    notice_id = int(request.data.get("notice_id", 101))
    profile = profile_from_request(request)
    profile.update(request.data.get("profile", {}))
    summary = coach_summary(notice_id, profile)
    if summary is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(summary)
