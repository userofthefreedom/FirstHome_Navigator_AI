from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.policies.services.matcher import match_policies
from apps.profiles.services import profile_from_request, save_last_recommendations
from apps.products.services.loan_matcher import match_purchase_loans
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import cached_recommendation_candidate_count, cached_ranked_recommendations
from apps.rules.cache_keys import cache_key, data_version, profile_hash
from apps.rules.cache_service import get_or_set_locked


RECOMMENDATION_LIMIT = 6


@api_view(["GET"])
def dashboard(request):
    profile = profile_from_request(request)
    recommendations = cached_ranked_recommendations(profile, limit=RECOMMENDATION_LIMIT)
    save_last_recommendations(request, recommendations)
    return Response(
        {
            "profile": profile,
            "top_recommendations": recommendations,
            "notice_count": cached_recommendation_candidate_count(profile),
            "message": "소유형 공공분양 공고를 기준으로 추천과 자금 로드맵을 계산합니다.",
        }
    )


@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    recommendations = cached_ranked_recommendations(profile, limit=RECOMMENDATION_LIMIT)
    save_last_recommendations(request, recommendations)
    return Response(recommendations)


@api_view(["GET"])
def product_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("product-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_products(profile), timeout=300))


@api_view(["GET"])
def loan_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("loan-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_purchase_loans(profile), timeout=300))


@api_view(["GET"])
def policy_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("policy-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_policies(profile), timeout=300))
