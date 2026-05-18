from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.services import calculate_score, default_profile, funding_plan, notices, policies, products


@api_view(["GET"])
def dashboard(request):
    profile = request.session.get("profile", default_profile())
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in notices()],
        key=lambda item: item["total_score"],
        reverse=True,
    )
    return Response(
        {
            "profile": profile,
            "top_recommendations": recommendations[:3],
            "notice_count": len(recommendations),
            "message": "fixture 기준으로 대표 USE CASE를 실행할 수 있습니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = request.session.get("profile", default_profile())
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in notices()],
        key=lambda item: item["total_score"],
        reverse=True,
    )
    return Response(recommendations[:3])


@api_view(["GET"])
def funding_recommendation(request, notice_id):
    profile = request.session.get("profile", default_profile())
    plan = funding_plan(notice_id, profile)
    if plan is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(plan)


@api_view(["GET"])
def product_recommendations(request):
    return Response(products())


@api_view(["GET"])
def policy_recommendations(request):
    return Response(policies())
