from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import current_notices
from apps.policies.services.matcher import match_policies
from apps.profiles.services import profile_from_request
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import ranked_recommendations


@api_view(["GET"])
def dashboard(request):
    profile = profile_from_request(request)
    recommendations = ranked_recommendations(profile, limit=3)
    return Response(
        {
            "profile": profile,
            "top_recommendations": recommendations,
            "notice_count": len(current_notices()),
            "message": "소유형 공공분양 공고를 기준으로 추천과 자금 로드맵을 계산합니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    return Response(ranked_recommendations(profile, limit=3))


@api_view(["GET"])
def product_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_products(profile))


@api_view(["GET"])
def policy_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_policies(profile))
