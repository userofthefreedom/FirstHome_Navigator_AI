from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.policies.services.matcher import match_policies
from apps.profiles.services import profile_from_request, save_last_recommendations
from apps.products.services.loan_matcher import match_purchase_loans
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import recommendation_candidate_notices, ranked_recommendations


RECOMMENDATION_LIMIT = 6


@api_view(["GET"])
def dashboard(request):
    profile = profile_from_request(request)
    recommendations = ranked_recommendations(profile, limit=RECOMMENDATION_LIMIT)
    save_last_recommendations(request, recommendations)
    return Response(
        {
            "profile": profile,
            "top_recommendations": recommendations,
            "notice_count": len(recommendation_candidate_notices(profile)),
            "message": "소유형 공공분양 공고를 기준으로 추천과 자금 로드맵을 계산합니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    recommendations = ranked_recommendations(profile, limit=RECOMMENDATION_LIMIT)
    save_last_recommendations(request, recommendations)
    return Response(recommendations)


@api_view(["GET"])
def product_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_products(profile))


@api_view(["GET"])
def loan_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_purchase_loans(profile))


@api_view(["GET"])
def policy_recommendations(request):
    profile = profile_from_request(request)
    return Response(match_policies(profile))
