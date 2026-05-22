from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.profiles.services import profile_from_request
from apps.services import coach_summary
from apps.ai_coach.services.prompt_templates import coach_chat


@api_view(["POST"])
def coach_summary_view(request):
    notice_id = int(request.data.get("notice_id", 101))
    profile = profile_from_request(request)
    profile.update(request.data.get("profile", {}))
    summary = coach_summary(notice_id, profile)
    if summary is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(summary)


@api_view(["POST"])
def coach_chat_view(request):
    try:
        notice_id = int(request.data.get("notice_id", 101))
    except ValueError:
        return Response({"detail": "notice_id must be an integer"}, status=400)
    option_id = request.data.get("option_id")
    message = str(request.data.get("message", "")).strip()
    profile = profile_from_request(request)
    profile.update(request.data.get("profile", {}))
    try:
        parsed_option_id = int(option_id) if option_id else None
    except ValueError:
        return Response({"detail": "option_id must be an integer"}, status=400)
    response = coach_chat(
        notice_id,
        message,
        profile,
        option_id=parsed_option_id,
    )
    if response is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(response)
