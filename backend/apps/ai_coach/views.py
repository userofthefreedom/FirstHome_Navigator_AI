from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import (
    COACH_CHAT_EXAMPLE,
    COACH_CHAT_REQUEST,
    COACH_CHAT_RESPONSE,
    COACH_SUMMARY_EXAMPLE,
    COACH_SUMMARY_REQUEST,
    COACH_SUMMARY_RESPONSE,
    COMMON_ERROR_RESPONSES,
    TAGS,
)
from apps.ai_coach.models import AiCoachPlan
from apps.ai_coach.services.prompt_templates import coach_chat, coach_summary
from apps.profiles.services import profile_from_request


@extend_schema(
    tags=[TAGS["ai"]],
    summary="AI 코치 요약 생성",
    description="선택 공고/주택형 옵션과 사용자 프로필을 바탕으로 이번 주 할 일, 공식 확인 포인트, 선택 기준을 생성합니다. 로그인 사용자는 LLM 결과를 캐시합니다.",
    request=COACH_SUMMARY_REQUEST,
    responses={200: COACH_SUMMARY_RESPONSE, **COMMON_ERROR_RESPONSES},
    examples=[COACH_SUMMARY_EXAMPLE],
)
@api_view(["POST"])
def coach_summary_view(request):
    notice_id = int(request.data.get("notice_id", 101))
    option_id = request.data.get("option_id")
    force_refresh = bool(request.data.get("force_refresh", False))
    profile = profile_from_request(request)
    profile.update(request.data.get("profile", {}))
    try:
        parsed_option_id = int(option_id) if option_id else None
    except ValueError:
        return Response({"detail": "option_id must be an integer"}, status=400)
    is_authenticated = bool(getattr(request.user, "is_authenticated", False))
    summary = coach_summary(
        notice_id,
        profile,
        option_id=parsed_option_id,
        user=request.user if is_authenticated else None,
        allow_llm=is_authenticated,
        force_refresh=force_refresh,
    )
    if summary is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(summary)


@extend_schema(
    tags=[TAGS["ai"]],
    summary="최근 AI 코치 요약 조회",
    description="대시보드에서 이미 생성된 AI 코치 결과만 가볍게 조회합니다. 새 LLM 분석은 실행하지 않습니다.",
    responses={200: COACH_SUMMARY_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def latest_coach_summary_view(request):
    if not getattr(request.user, "is_authenticated", False):
        return Response({"exists": False, "requires_login": True})

    base_queryset = AiCoachPlan.objects.filter(user=request.user)
    queryset = base_queryset
    notice_id = request.query_params.get("notice_id")
    option_id = request.query_params.get("option_id")
    try:
        if notice_id:
            queryset = queryset.filter(notice_id=int(notice_id))
        if option_id:
            queryset = queryset.filter(option_id=int(option_id))
    except ValueError:
        return Response({"detail": "notice_id and option_id must be integers"}, status=400)

    cached = queryset.first()
    if not cached and notice_id and option_id:
        cached = base_queryset.filter(notice_id=int(notice_id)).first()
    if not cached:
        return Response({"exists": False, "requires_login": False})

    payload = dict(cached.payload or {})
    payload["exists"] = True
    payload["source"] = "cached_llm" if payload.get("source") == "llm" else payload.get("source", "cached")
    payload["cached_at"] = cached.updated_at.isoformat()
    payload["requires_login"] = False
    payload.setdefault("notice_id", cached.notice_id)
    payload.setdefault("option_id", cached.option_id or None)
    return Response(payload)


@extend_schema(
    tags=[TAGS["ai"]],
    summary="전역 AI 챗봇 답변",
    description="현재 화면 context, 선택 공고, 선택 옵션, 사용자 조건을 바탕으로 청약 관련 질문에 답변합니다.",
    request=COACH_CHAT_REQUEST,
    responses={200: COACH_CHAT_RESPONSE, **COMMON_ERROR_RESPONSES},
    examples=[COACH_CHAT_EXAMPLE],
)
@api_view(["POST"])
def coach_chat_view(request):
    try:
        notice_id = int(request.data.get("notice_id", 101))
    except ValueError:
        return Response({"detail": "notice_id must be an integer"}, status=400)
    option_id = request.data.get("option_id")
    message = str(request.data.get("message", "")).strip()
    page_context = request.data.get("page_context", {})
    if not isinstance(page_context, dict):
        page_context = {}
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
        page_context=page_context,
    )
    if response is None:
        return Response({"detail": "notice not found"}, status=404)
    return Response(response)
