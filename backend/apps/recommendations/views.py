from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import DASHBOARD_RESPONSE, RECOMMENDATION_LIST_RESPONSE, TAGS
from apps.policies.services.matcher import match_policies
from apps.profiles.services import profile_from_request, save_last_recommendations
from apps.products.services.loan_matcher import match_purchase_loans
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import cached_recommendation_candidate_count, cached_ranked_recommendations
from apps.rules.cache_keys import cache_key, data_version, profile_hash
from apps.rules.cache_service import get_or_set_locked


RECOMMENDATION_LIMIT = 6


@extend_schema(
    tags=[TAGS["recommendations"]],
    summary="대시보드 추천 요약",
    description="현재 프로필 기준 상위 청약 후보, 후보 수, 사용자 조건을 대시보드용으로 반환합니다.",
    responses={200: DASHBOARD_RESPONSE},
)
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


@extend_schema(
    tags=[TAGS["recommendations"]],
    summary="추천 청약 목록",
    description="사용자 조건과 실제/fixture 보충 공고를 바탕으로 청약 후보를 점수순으로 반환합니다.",
    responses={200: RECOMMENDATION_LIST_RESPONSE},
)
@api_view(["GET"])
def housing_recommendations(request):
    profile = profile_from_request(request)
    recommendations = cached_ranked_recommendations(profile, limit=RECOMMENDATION_LIMIT)
    save_last_recommendations(request, recommendations)
    return Response(recommendations)


@extend_schema(
    tags=[TAGS["recommendations"]],
    summary="추천 금융상품 목록",
    description="사용자 자금 조건에 맞는 예금/적금 상품 후보를 반환합니다.",
    responses={200: {"type": "array", "items": {"type": "object"}}},
)
@api_view(["GET"])
def product_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("product-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_products(profile), timeout=300))


@extend_schema(
    tags=[TAGS["recommendations"]],
    summary="추천 주택담보대출 목록",
    description="선택 청약과 사용자 자금 조건에 맞는 주택구입 목적 대출 후보를 반환합니다.",
    responses={200: {"type": "array", "items": {"type": "object"}}},
)
@api_view(["GET"])
def loan_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("loan-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_purchase_loans(profile), timeout=300))


@extend_schema(
    tags=[TAGS["recommendations"]],
    summary="추천 청년정책 목록",
    description="사용자 지역, 소득, 청약 준비 상황에 맞는 청년정책 후보를 반환합니다.",
    responses={200: {"type": "array", "items": {"type": "object"}}},
)
@api_view(["GET"])
def policy_recommendations(request):
    profile = profile_from_request(request)
    key = cache_key("policy-recommendations", data_version(), profile_hash(profile))
    return Response(get_or_set_locked(key, lambda: match_policies(profile), timeout=300))
