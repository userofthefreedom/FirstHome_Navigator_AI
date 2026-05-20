from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.profiles.services import profile_from_request
from apps.services import funding_plan, match_policies, match_products, notices, ranked_recommendations


@api_view(["GET"])
def dashboard(request):
    profile = profile_from_request(request)
    recommendations = ranked_recommendations(profile, limit=3)
    return Response(
        {
            "profile": profile,
            "top_recommendations": recommendations,
            "notice_count": len(notices()),
            "message": "fixture 기준으로 대표 USE CASE를 끝까지 실행할 수 있습니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    return Response(ranked_recommendations(profile, limit=3))


@api_view(["GET"])
def funding_recommendation(request, notice_id):
    profile = profile_from_request(request)
    plan = funding_plan(notice_id, profile)
    if plan is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(plan)


@api_view(["GET"])
def product_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_products(profile))


@api_view(["GET"])
def policy_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_policies(profile))
