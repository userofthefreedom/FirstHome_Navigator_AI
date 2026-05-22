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
            "message": "소유형 공공분양 공고만 기준으로 추천과 자금 로드맵을 계산합니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    return Response(ranked_recommendations(profile, limit=3))


@api_view(["GET"])
def funding_recommendation(request, notice_id):
    profile = profile_from_request(request)
    option_id = request.query_params.get("option_id")
    try:
        parsed_option_id = int(option_id) if option_id else None
    except ValueError:
        return Response({"detail": "option_id must be an integer"}, status=400)
    plan = funding_plan(notice_id, profile, option_id=parsed_option_id)
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
