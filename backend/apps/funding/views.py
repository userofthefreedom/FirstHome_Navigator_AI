from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.funding.services.calculator import funding_plan
from apps.profiles.services import profile_from_request
from apps.rules.cache_keys import cache_key, data_version, profile_hash
from apps.rules.cache_service import get_or_set_locked


@api_view(["GET"])
def funding_recommendation(request, notice_id):
    profile = profile_from_request(request)
    option_id = request.query_params.get("option_id")
    try:
        parsed_option_id = int(option_id) if option_id else None
    except ValueError:
        return Response({"detail": "option_id must be an integer"}, status=400)
    key = cache_key("funding-plan", data_version(), profile_hash(profile), notice_id, parsed_option_id or "notice")
    plan = get_or_set_locked(key, lambda: funding_plan(notice_id, profile, option_id=parsed_option_id), timeout=300)
    if plan is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(plan)
