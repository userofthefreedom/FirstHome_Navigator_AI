from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, inline_serializer
from rest_framework import serializers

from apps.community.serializers import AgoraCommentSerializer, AgoraPostSerializer
from apps.products.serializers import FinancialProductSerializer, UserJoinedProductSerializer
from apps.profiles.serializers import UserProfileSerializer


TAGS = {
    "auth": "Auth / Account",
    "profile": "Profile",
    "notices": "Housing Notices",
    "notice_docs": "Notice Documents",
    "recommendations": "Recommendations",
    "funding": "Funding",
    "ai": "AI Coach",
    "products": "Financial Products",
    "market": "Market",
    "places": "Map / Places",
    "community": "Community",
    "videos": "Videos",
}


TAG_SETTINGS = [
    {"name": TAGS["auth"], "description": "회원가입, 로그인, 로그아웃, 현재 사용자와 계정 상태 API입니다."},
    {"name": TAGS["profile"], "description": "사용자 청약 조건, 관심 항목, 현재 선택 공고/옵션 상태 API입니다."},
    {"name": TAGS["notices"], "description": "LH 청약 공고 목록, 상세, 지도 표시용 공고 API입니다."},
    {"name": TAGS["notice_docs"], "description": "공식 공고문 발견/분석, 주택형 옵션, 자격 체크리스트 API입니다."},
    {"name": TAGS["recommendations"], "description": "청약, 금융상품, 주택담보대출, 정책 추천 API입니다."},
    {"name": TAGS["funding"], "description": "선택 공고와 주택형 옵션 기준 자금 로드맵 API입니다."},
    {"name": TAGS["ai"], "description": "SSAFY GMS/OpenAI-compatible LLM 기반 AI 코치와 전역 챗봇 API입니다."},
    {"name": TAGS["products"], "description": "금융상품 목록/상세, 가입상품 저장과 해제 API입니다."},
    {"name": TAGS["market"], "description": "Economy NOW 시장 지표와 주거 시장 보조 지표 API입니다."},
    {"name": TAGS["places"], "description": "Kakao Local REST API와 Kakao 길찾기 기반 주변 은행, 부동산, 경로 API입니다."},
    {"name": TAGS["community"], "description": "청약 아고라 게시글과 댓글 API입니다."},
    {"name": TAGS["videos"], "description": "YouTube 기반 청약 관련 영상 검색 API입니다."},
]


ERROR_RESPONSE = inline_serializer(
    name="ErrorResponse",
    fields={"detail": serializers.CharField(help_text="오류 메시지")},
)


USER_RESPONSE = inline_serializer(
    name="UserResponse",
    fields={
        "is_authenticated": serializers.BooleanField(),
        "id": serializers.IntegerField(required=False),
        "username": serializers.CharField(required=False),
        "email": serializers.EmailField(required=False, allow_blank=True),
    },
)


AUTH_REQUEST = inline_serializer(
    name="AuthCredentialRequest",
    fields={
        "username": serializers.CharField(help_text="사용자 아이디"),
        "password": serializers.CharField(write_only=True, help_text="비밀번호"),
        "email": serializers.EmailField(required=False, allow_blank=True, help_text="회원가입 시 선택 입력"),
        "name": serializers.CharField(required=False, allow_blank=True, help_text="회원가입 시 조건 입력 기본값으로 저장할 이름"),
        "birth_year": serializers.IntegerField(required=False, help_text="회원가입 시 조건 입력 기본값으로 저장할 출생년도"),
    },
)


AUTH_RESPONSE = inline_serializer(
    name="AuthResponse",
    fields={
        "user": USER_RESPONSE,
        "profile": UserProfileSerializer(required=False),
        "account_state": serializers.DictField(required=False),
    },
)


LOGOUT_RESPONSE = inline_serializer(
    name="LogoutResponse",
    fields={"user": USER_RESPONSE},
)


PROFILE_RESPONSE = UserProfileSerializer


ACCOUNT_STATE_REQUEST = inline_serializer(
    name="AccountStateRequest",
    fields={
        "current_notice_id": serializers.IntegerField(required=False, allow_null=True),
        "current_option_id": serializers.IntegerField(required=False, allow_null=True),
        "last_recommendations": serializers.ListField(child=serializers.DictField(), required=False),
        "last_funding_plan": serializers.DictField(required=False),
    },
)


ACCOUNT_STATE_RESPONSE = inline_serializer(
    name="AccountStateResponse",
    fields={
        "current_notice_id": serializers.IntegerField(required=False, allow_null=True),
        "current_option_id": serializers.IntegerField(required=False, allow_null=True),
        "last_recommendations": serializers.ListField(child=serializers.DictField(), required=False),
        "last_funding_plan": serializers.DictField(required=False),
    },
)


FAVORITE_REQUEST = inline_serializer(
    name="FavoriteRequest",
    fields={
        "favorite_type": serializers.ChoiceField(choices=["notice", "option", "product", "policy"]),
        "object_id": serializers.IntegerField(),
    },
)


FAVORITE_RESPONSE = inline_serializer(
    name="FavoriteResponse",
    fields={
        "id": serializers.IntegerField(required=False),
        "favorite_type": serializers.CharField(),
        "object_id": serializers.IntegerField(),
        "created_at": serializers.DateTimeField(required=False),
        "item": serializers.DictField(required=False, allow_null=True),
    },
)


FAVORITE_LIST_RESPONSE = inline_serializer(
    name="FavoriteListResponse",
    many=True,
    fields={
        "id": serializers.IntegerField(required=False),
        "favorite_type": serializers.CharField(),
        "object_id": serializers.IntegerField(),
        "created_at": serializers.DateTimeField(required=False),
        "item": serializers.DictField(required=False, allow_null=True),
    },
)


NOTICE_RESPONSE = inline_serializer(
    name="HousingNoticeResponse",
    fields={
        "id": serializers.IntegerField(),
        "title": serializers.CharField(),
        "provider": serializers.CharField(),
        "region": serializers.CharField(),
        "district": serializers.CharField(required=False, allow_blank=True),
        "supply_type": serializers.CharField(required=False, allow_blank=True),
        "housing_type": serializers.CharField(required=False, allow_blank=True),
        "area": serializers.CharField(required=False, allow_blank=True),
        "price": serializers.IntegerField(required=False),
        "application_deadline": serializers.CharField(required=False, allow_blank=True),
        "winner_date": serializers.CharField(required=False, allow_blank=True),
        "contract_date": serializers.CharField(required=False, allow_blank=True),
        "move_in": serializers.CharField(required=False, allow_blank=True),
        "source_url": serializers.URLField(required=False, allow_blank=True),
        "data_source": serializers.CharField(required=False, allow_blank=True),
        "is_service_target": serializers.BooleanField(required=False),
        "analysis_summary": serializers.DictField(required=False),
        "official_document_status": serializers.CharField(required=False, allow_blank=True),
        "unit_option_count": serializers.IntegerField(required=False),
        "document_count": serializers.IntegerField(required=False),
    },
)


NOTICE_LIST_RESPONSE = inline_serializer(
    name="HousingNoticeListResponse",
    many=True,
    fields={
        "id": serializers.IntegerField(),
        "title": serializers.CharField(),
        "provider": serializers.CharField(),
        "region": serializers.CharField(),
        "district": serializers.CharField(required=False, allow_blank=True),
        "supply_type": serializers.CharField(required=False, allow_blank=True),
        "housing_type": serializers.CharField(required=False, allow_blank=True),
        "price": serializers.IntegerField(required=False),
        "application_deadline": serializers.CharField(required=False, allow_blank=True),
        "source_url": serializers.URLField(required=False, allow_blank=True),
        "data_source": serializers.CharField(required=False, allow_blank=True),
        "is_service_target": serializers.BooleanField(required=False),
        "analysis_summary": serializers.DictField(required=False),
        "official_document_status": serializers.CharField(required=False, allow_blank=True),
        "unit_option_count": serializers.IntegerField(required=False),
        "document_count": serializers.IntegerField(required=False),
    },
)


SCORE_DETAIL = inline_serializer(
    name="RecommendationScoreDetail",
    fields={
        "eligibility": serializers.IntegerField(required=False),
        "funding": serializers.IntegerField(required=False),
        "location": serializers.IntegerField(required=False),
        "schedule": serializers.IntegerField(required=False),
        "source_penalty": serializers.IntegerField(required=False),
    },
)


RECOMMENDATION_RESPONSE = inline_serializer(
    name="HousingRecommendationResponse",
    fields={
        **NOTICE_RESPONSE.fields,
        "total_score": serializers.IntegerField(required=False),
        "score_max": serializers.IntegerField(required=False),
        "score_detail": serializers.DictField(required=False),
        "reasons": serializers.ListField(child=serializers.CharField(), required=False),
        "best_option": serializers.DictField(required=False),
        "top_options": serializers.ListField(child=serializers.DictField(), required=False),
        "funding_plan": serializers.DictField(required=False),
    },
)


RECOMMENDATION_LIST_RESPONSE = inline_serializer(
    name="HousingRecommendationListResponse",
    many=True,
    fields={
        "id": serializers.IntegerField(),
        "title": serializers.CharField(),
        "provider": serializers.CharField(required=False),
        "region": serializers.CharField(required=False),
        "district": serializers.CharField(required=False, allow_blank=True),
        "price": serializers.IntegerField(required=False),
        "application_deadline": serializers.CharField(required=False, allow_blank=True),
        "total_score": serializers.IntegerField(required=False),
        "score_max": serializers.IntegerField(required=False),
        "score_detail": serializers.DictField(required=False),
        "reasons": serializers.ListField(child=serializers.CharField(), required=False),
        "best_option": serializers.DictField(required=False),
        "top_options": serializers.ListField(child=serializers.DictField(), required=False),
    },
)


DASHBOARD_RESPONSE = inline_serializer(
    name="DashboardResponse",
    fields={
        "profile": serializers.DictField(),
        "top_recommendations": serializers.ListField(child=serializers.DictField()),
        "notice_count": serializers.IntegerField(),
        "message": serializers.CharField(),
    },
)


DOCUMENT_RESPONSE = inline_serializer(
    name="NoticeDocumentResponse",
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "provider": serializers.CharField(),
        "file_id": serializers.CharField(required=False, allow_blank=True),
        "file_name": serializers.CharField(required=False, allow_blank=True),
        "document_url": serializers.URLField(required=False, allow_blank=True),
        "source_url": serializers.URLField(required=False, allow_blank=True),
        "status": serializers.CharField(),
        "error_message": serializers.CharField(required=False, allow_blank=True),
        "fetched_at": serializers.CharField(required=False, allow_blank=True),
        "analyzed_at": serializers.CharField(required=False, allow_blank=True),
    },
)


EVIDENCE_RESPONSE = inline_serializer(
    name="ExtractionEvidenceResponse",
    fields={
        "id": serializers.IntegerField(),
        "field_path": serializers.CharField(),
        "page_no": serializers.IntegerField(allow_null=True),
        "source_text": serializers.CharField(),
        "confidence": serializers.FloatField(),
    },
)


EXTRACTION_RESPONSE = inline_serializer(
    name="NoticeExtractionResponse",
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "document_id": serializers.IntegerField(),
        "schema_version": serializers.CharField(),
        "status": serializers.CharField(),
        "confidence": serializers.FloatField(),
        "source": serializers.CharField(required=False, allow_blank=True),
        "option_count": serializers.IntegerField(required=False),
        "warnings": serializers.DictField(required=False),
        "evidence": serializers.ListField(child=serializers.DictField(), required=False),
        "created_at": serializers.CharField(required=False, allow_blank=True),
    },
)


PAYMENT_SCHEDULE_RESPONSE = inline_serializer(
    name="PaymentScheduleResponse",
    fields={
        "id": serializers.IntegerField(),
        "label": serializers.CharField(),
        "due_date": serializers.CharField(required=False, allow_blank=True),
        "amount": serializers.IntegerField(),
        "payment_type": serializers.CharField(),
        "sequence": serializers.IntegerField(),
        "evidence_text": serializers.CharField(required=False, allow_blank=True),
    },
)


UNIT_OPTION_RESPONSE = inline_serializer(
    name="HousingUnitOptionResponse",
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "document_id": serializers.IntegerField(allow_null=True),
        "extraction_id": serializers.IntegerField(allow_null=True),
        "extraction_schema_version": serializers.CharField(required=False, allow_blank=True),
        "extraction_status": serializers.CharField(required=False, allow_blank=True),
        "extraction_source": serializers.CharField(required=False, allow_blank=True),
        "unit_type": serializers.CharField(),
        "exclusive_area_m2": serializers.FloatField(),
        "floor_group": serializers.CharField(required=False, allow_blank=True),
        "option_type": serializers.CharField(required=False, allow_blank=True),
        "base_price": serializers.IntegerField(),
        "loan_amount": serializers.IntegerField(required=False),
        "balcony_extension_price": serializers.IntegerField(required=False),
        "confidence": serializers.FloatField(required=False),
        "confidence_reasons": serializers.ListField(child=serializers.CharField(), required=False),
        "source_page": serializers.IntegerField(required=False, allow_null=True),
        "source_text": serializers.CharField(required=False, allow_blank=True),
        "payment_schedules": serializers.ListField(child=serializers.DictField(), required=False),
    },
)


UNIT_OPTION_LIST_RESPONSE = inline_serializer(
    name="HousingUnitOptionListResponse",
    many=True,
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "document_id": serializers.IntegerField(allow_null=True),
        "extraction_id": serializers.IntegerField(allow_null=True),
        "unit_type": serializers.CharField(),
        "exclusive_area_m2": serializers.FloatField(),
        "floor_group": serializers.CharField(required=False, allow_blank=True),
        "option_type": serializers.CharField(required=False, allow_blank=True),
        "base_price": serializers.IntegerField(),
        "loan_amount": serializers.IntegerField(required=False),
        "balcony_extension_price": serializers.IntegerField(required=False),
        "confidence": serializers.FloatField(required=False),
        "confidence_reasons": serializers.ListField(child=serializers.CharField(), required=False),
        "source_page": serializers.IntegerField(required=False, allow_null=True),
        "source_text": serializers.CharField(required=False, allow_blank=True),
        "payment_schedules": serializers.ListField(child=serializers.DictField(), required=False),
    },
)


CHECKLIST_RESPONSE = inline_serializer(
    name="EligibilityChecklistResponse",
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "document_id": serializers.IntegerField(allow_null=True),
        "category": serializers.CharField(),
        "title": serializers.CharField(),
        "condition_text": serializers.CharField(),
        "evidence_text": serializers.CharField(required=False, allow_blank=True),
        "page_no": serializers.IntegerField(required=False, allow_null=True),
        "confidence": serializers.FloatField(),
    },
)


CHECKLIST_LIST_RESPONSE = inline_serializer(
    name="EligibilityChecklistListResponse",
    many=True,
    fields={
        "id": serializers.IntegerField(),
        "notice_id": serializers.IntegerField(),
        "document_id": serializers.IntegerField(allow_null=True),
        "category": serializers.CharField(),
        "title": serializers.CharField(),
        "condition_text": serializers.CharField(),
        "evidence_text": serializers.CharField(required=False, allow_blank=True),
        "page_no": serializers.IntegerField(required=False, allow_null=True),
        "confidence": serializers.FloatField(),
    },
)


DOCUMENT_STATUS_RESPONSE = inline_serializer(
    name="NoticeDocumentStatusResponse",
    fields={
        "notice_id": serializers.IntegerField(required=False),
        "official_document_status": serializers.CharField(required=False),
        "analysis_summary": serializers.DictField(required=False),
        "documents": serializers.ListField(child=serializers.DictField()),
        "latest_extraction": serializers.DictField(required=False, allow_null=True),
    },
)


ANALYZE_REQUEST = inline_serializer(
    name="AnalyzeNoticeDocumentRequest",
    fields={"async": serializers.BooleanField(required=False, help_text="true이면 pending 상태로 분석을 시작합니다.")},
)


ANALYZE_RESPONSE = inline_serializer(
    name="AnalyzeNoticeDocumentResponse",
    fields={
        "notice_id": serializers.IntegerField(),
        "official_document_status": serializers.CharField(),
        "document": serializers.DictField(),
        "extraction": serializers.DictField(required=False),
        "unit_options": serializers.ListField(child=serializers.DictField(), required=False),
        "analysis_summary": serializers.DictField(required=False),
        "already_pending": serializers.BooleanField(required=False),
        "message": serializers.CharField(),
    },
)


FUNDING_RESPONSE = inline_serializer(
    name="FundingPlanResponse",
    fields={
        "notice_id": serializers.IntegerField(required=False),
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "notice_title": serializers.CharField(required=False, allow_blank=True),
        "price": serializers.IntegerField(required=False),
        "required_cash": serializers.IntegerField(required=False),
        "available_cash": serializers.IntegerField(required=False),
        "shortage": serializers.IntegerField(required=False),
        "monthly_saving": serializers.IntegerField(required=False),
        "months_until_due": serializers.IntegerField(required=False),
        "timeline": serializers.ListField(child=serializers.DictField(), required=False),
        "insights": serializers.ListField(child=serializers.DictField(), required=False),
        "loan_candidates": serializers.ListField(child=serializers.DictField(), required=False),
        "schedule_source": serializers.CharField(required=False, allow_blank=True),
    },
)


COACH_SUMMARY_REQUEST = inline_serializer(
    name="CoachSummaryRequest",
    fields={
        "notice_id": serializers.IntegerField(default=101),
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "force_refresh": serializers.BooleanField(required=False, default=False),
        "profile": serializers.DictField(required=False),
    },
)


COACH_SUMMARY_RESPONSE = inline_serializer(
    name="CoachSummaryResponse",
    fields={
        "source": serializers.CharField(),
        "notice_id": serializers.IntegerField(required=False),
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "requires_login": serializers.BooleanField(required=False),
        "summary": serializers.CharField(),
        "todo_this_week": serializers.ListField(child=serializers.CharField(), required=False),
        "official_checklist": serializers.ListField(child=serializers.CharField(), required=False),
        "deep_review_items": serializers.ListField(child=serializers.DictField(), required=False),
        "decision_points": serializers.ListField(child=serializers.DictField(), required=False),
        "warning": serializers.CharField(required=False),
        "context_refs": serializers.ListField(child=serializers.DictField(), required=False),
    },
)


COACH_CHAT_REQUEST = inline_serializer(
    name="CoachChatRequest",
    fields={
        "notice_id": serializers.IntegerField(default=101),
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "message": serializers.CharField(),
        "profile": serializers.DictField(required=False),
        "page_context": serializers.DictField(required=False),
    },
)


COACH_CHAT_RESPONSE = inline_serializer(
    name="CoachChatResponse",
    fields={
        "source": serializers.CharField(),
        "notice_id": serializers.IntegerField(required=False),
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "reply": serializers.CharField(),
        "suggested_actions": serializers.ListField(child=serializers.CharField(), required=False),
        "context_refs": serializers.ListField(child=serializers.DictField(), required=False),
        "page_context": serializers.DictField(required=False),
    },
)


PRODUCT_LIST_RESPONSE = inline_serializer(
    name="FinancialProductListResponse",
    fields={
        "items": serializers.ListField(child=serializers.DictField()),
        "filters": serializers.DictField(),
    },
)


JOIN_PRODUCT_REQUEST = inline_serializer(
    name="JoinProductRequest",
    fields={
        "option_id": serializers.IntegerField(required=False, allow_null=True),
        "memo": serializers.CharField(required=False, allow_blank=True, max_length=200),
    },
)


MARKET_PRICE_RESPONSE = inline_serializer(
    name="MarketPriceResponse",
    fields={
        "date": serializers.DateField(),
        "price": serializers.FloatField(),
        "change_rate": serializers.FloatField(),
        "source": serializers.CharField(),
        "region_code": serializers.CharField(required=False, allow_blank=True),
        "region_name": serializers.CharField(required=False, allow_blank=True),
        "source_meta": serializers.DictField(required=False),
        "unit": serializers.CharField(required=False, allow_blank=True),
    },
)


MARKET_ASSETS_RESPONSE = inline_serializer(
    name="MarketAssetsResponse",
    fields={
        "asset": serializers.CharField(),
        "label": serializers.CharField(),
        "unit": serializers.CharField(required=False, allow_blank=True),
        "items": serializers.ListField(child=serializers.DictField()),
        "regions": serializers.ListField(child=serializers.DictField(), required=False),
        "source": serializers.CharField(),
        "is_fixture": serializers.BooleanField(),
        "detail": serializers.CharField(required=False, allow_blank=True),
    },
)


MARKET_SUMMARY_RESPONSE = inline_serializer(
    name="MarketSummaryResponse",
    fields={
        "cards": serializers.ListField(child=serializers.DictField()),
        "stats": serializers.ListField(child=serializers.DictField()),
    },
)


PLACE_RESPONSE = inline_serializer(
    name="PlaceResponse",
    fields={
        "id": serializers.CharField(),
        "name": serializers.CharField(),
        "category": serializers.CharField(),
        "address": serializers.CharField(required=False, allow_blank=True),
        "road_address": serializers.CharField(required=False, allow_blank=True),
        "phone": serializers.CharField(required=False, allow_blank=True),
        "distance": serializers.IntegerField(required=False),
        "lat": serializers.FloatField(),
        "lng": serializers.FloatField(),
        "place_url": serializers.URLField(required=False, allow_blank=True),
        "direction_url": serializers.URLField(required=False, allow_blank=True),
    },
)


PLACES_SEARCH_RESPONSE = inline_serializer(
    name="PlacesSearchResponse",
    fields={
        "items": serializers.ListField(child=serializers.DictField()),
        "fallback": serializers.BooleanField(),
        "center": serializers.DictField(required=False),
    },
)


ROUTE_RESPONSE = inline_serializer(
    name="RouteResponse",
    fields={
        "origin": serializers.DictField(),
        "destination": serializers.DictField(),
        "direction_url": serializers.URLField(),
        "polyline": serializers.ListField(child=serializers.DictField()),
        "distance": serializers.IntegerField(required=False, allow_null=True),
        "duration": serializers.IntegerField(required=False, allow_null=True),
        "message": serializers.CharField(),
        "fallback": serializers.BooleanField(required=False),
    },
)


VIDEO_RESPONSE = inline_serializer(
    name="VideoResponse",
    fields={
        "video_id": serializers.CharField(),
        "title": serializers.CharField(),
        "channel_title": serializers.CharField(),
        "published_at": serializers.CharField(),
        "thumbnail_url": serializers.URLField(required=False, allow_blank=True),
        "description": serializers.CharField(required=False, allow_blank=True),
    },
)


VIDEOS_RESPONSE = inline_serializer(
    name="VideosResponse",
    fields={
        "items": serializers.ListField(child=serializers.DictField()),
        "fallback": serializers.BooleanField(),
        "fallback_reason": serializers.CharField(required=False),
    },
)


def list_response(serializer):
    return inline_serializer(
        name=f"{serializer.__name__ if hasattr(serializer, '__name__') else serializer.__class__.__name__}List",
        fields={"items": serializers.ListField(child=serializers.DictField())},
    )


BOOLEAN_QUERY = OpenApiTypes.BOOL

CLIENT_ID_HEADER = OpenApiParameter(
    name="X-FirstHome-Client-Id",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    required=False,
    description="비로그인 사용자의 관심 항목을 브라우저 단위로 유지하기 위한 클라이언트 ID입니다.",
)


ACTIVE_PARAM = OpenApiParameter("active", BOOLEAN_QUERY, OpenApiParameter.QUERY, description="1/true/yes이면 접수 가능한 활성 공고만 반환합니다.")
INCLUDE_EXCLUDED_PARAM = OpenApiParameter(
    "include_excluded",
    BOOLEAN_QUERY,
    OpenApiParameter.QUERY,
    description="1/true/yes이면 서비스 대상에서 제외된 공고까지 포함합니다.",
)
REGION_PARAM = OpenApiParameter("region", OpenApiTypes.STR, OpenApiParameter.QUERY, description="광역시·도 또는 지역명 필터입니다.")
OWNERSHIP_TYPE_PARAM = OpenApiParameter(
    "ownership_type",
    OpenApiTypes.STR,
    OpenApiParameter.QUERY,
    description="소유형/임대형 등 청약 유형 필터입니다.",
)
OPTION_ID_PARAM = OpenApiParameter("option_id", OpenApiTypes.INT, OpenApiParameter.QUERY, description="선택 주택형 옵션 ID입니다.")
ASYNC_PARAM = OpenApiParameter("async", BOOLEAN_QUERY, OpenApiParameter.QUERY, description="1이면 문서 분석을 비동기로 시작합니다.")


NOTICE_LIST_EXAMPLE = OpenApiExample(
    "활성 공고 목록 예시",
    value=[
        {
            "id": 1,
            "title": "서울 공공분양 예시",
            "provider": "LH",
            "region": "서울",
            "district": "강남구",
            "price": 520000000,
            "application_deadline": "2026-07-15",
            "data_source": "database",
        }
    ],
    response_only=True,
)

COACH_CHAT_EXAMPLE = OpenApiExample(
    "AI 챗봇 요청 예시",
    value={
        "notice_id": 1,
        "option_id": 250,
        "message": "이 옵션의 계약금 부족액과 공식 확인 포인트를 알려줘",
        "profile": {"asset": 12000000, "monthly_saving": 1000000},
        "page_context": {"path": "/ai-coach", "page_type": "ai_coach"},
    },
    request_only=True,
)

COACH_SUMMARY_EXAMPLE = OpenApiExample(
    "AI 코치 요청 예시",
    value={
        "notice_id": 1,
        "option_id": 250,
        "profile": {"asset": 12000000, "monthly_saving": 1000000},
        "force_refresh": False,
    },
    request_only=True,
)

JOIN_PRODUCT_EXAMPLE = OpenApiExample(
    "가입상품 저장 예시",
    value={"option_id": 15, "memo": "청약 계약금 마련용 적금 후보"},
    request_only=True,
)


COMMON_ERROR_RESPONSES = {
    400: ERROR_RESPONSE,
    401: ERROR_RESPONSE,
    403: ERROR_RESPONSE,
    404: ERROR_RESPONSE,
}


MODEL_RESPONSES = {
    "product": FinancialProductSerializer,
    "joined_product": UserJoinedProductSerializer,
    "post": AgoraPostSerializer,
    "comment": AgoraCommentSerializer,
}
