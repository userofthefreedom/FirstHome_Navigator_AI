from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import (
    ACCOUNT_STATE_REQUEST,
    ACCOUNT_STATE_RESPONSE,
    AUTH_REQUEST,
    AUTH_RESPONSE,
    CLIENT_ID_HEADER,
    COMMON_ERROR_RESPONSES,
    ERROR_RESPONSE,
    FAVORITE_LIST_RESPONSE,
    FAVORITE_REQUEST,
    FAVORITE_RESPONSE,
    LOGOUT_RESPONSE,
    PROFILE_RESPONSE,
    TAGS,
    USER_RESPONSE,
)
from apps.fixture_store import default_profile, find_notice, policies, products
from apps.notice_docs.models import HousingUnitOption
from apps.notice_docs.serializers import serialize_unit_option
from apps.profiles.models import Favorite, UserProfile
from apps.profiles.serializers import UserProfileSerializer
from apps.profiles.services import (
    PROFILE_FIELDS,
    account_state_payload as _account_state_payload,
    django_user as _django_user,
    profile_is_default_like as _profile_is_default_like,
    profile_defaults as _profile_defaults,
    profile_payload as _profile_payload,
    update_account_state_from_payload as _update_account_state_from_payload,
    user_account_state as _state_for_user,
    user_profile as _profile_for_user,
)


def _client_id(request) -> str:
    header_value = request.headers.get("X-FirstHome-Client-Id", "").strip()
    if header_value:
        return header_value[:64]

    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or "anonymous"


def _serialize_user(user) -> dict:
    if not user.is_authenticated:
        return {"is_authenticated": False}
    return {
        "is_authenticated": True,
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def _merge_session_profile(request, user) -> None:
    session_profile = request.session.get("profile")
    if not session_profile:
        return
    profile = _profile_for_user(user)
    if not _profile_is_default_like(_profile_payload(profile)):
        return
    for field in PROFILE_FIELDS:
        if field in session_profile:
            setattr(profile, field, session_profile[field])
    profile.save()


def _session_account_state(request) -> dict:
    return _account_state_payload(request.session.get("account_state", {}))


def _merge_session_account_state(request, user) -> None:
    session_state = _session_account_state(request)
    if not session_state.get("current_notice_id"):
        return
    state = _state_for_user(user)
    if state.current_notice_id:
        return
    _update_account_state_from_payload(state, session_state)


def _merge_client_favorites(request, user) -> None:
    client_id = request.headers.get("X-FirstHome-Client-Id", "").strip()
    if not client_id:
        return
    client_favorites = Favorite.objects.filter(user__isnull=True, client_id=client_id[:64])
    for favorite in client_favorites:
        Favorite.objects.get_or_create(
            user=user,
            favorite_type=favorite.favorite_type,
            object_id=favorite.object_id,
            defaults={"client_id": None},
        )
    client_favorites.delete()


def _favorite_item(favorite: Favorite | dict) -> dict | None:
    favorite_type = favorite.favorite_type if isinstance(favorite, Favorite) else favorite["favorite_type"]
    object_id = int(favorite.object_id if isinstance(favorite, Favorite) else favorite["object_id"])
    if favorite_type == "notice":
        notice = find_notice(object_id)
        if notice is None:
            return None
        option = _representative_option_for_notice(object_id)
        if option:
            notice = {**notice, "representative_option": option}
        return notice
    if favorite_type == "option":
        try:
            option = HousingUnitOption.objects.select_related("notice", "extraction").prefetch_related("payment_schedules").get(id=object_id)
        except HousingUnitOption.DoesNotExist:
            return None
        return {
            **serialize_unit_option(option),
            "title": f"{option.notice.title} {option.unit_type}",
            "name": f"{option.unit_type} {option.floor_group}".strip(),
            "provider": option.notice.provider,
            "region": option.notice.region,
            "source_url": option.notice.source_url,
        }
    if favorite_type == "product":
        return next((product for product in products() if product["id"] == object_id), None)
    if favorite_type == "policy":
        return next((policy for policy in policies() if policy["id"] == object_id), None)
    return None


def _representative_option_for_notice(notice_id: int) -> dict | None:
    option = (
        HousingUnitOption.objects.filter(notice_id=notice_id, base_price__gt=0, exclusive_area_m2__gt=0)
        .prefetch_related("payment_schedules")
        .order_by("-confidence", "base_price", "id")
        .first()
    )
    if option is None:
        return None
    return serialize_unit_option(option)


def _serialize_favorite(favorite: Favorite | dict) -> dict:
    if isinstance(favorite, Favorite):
        payload = {
            "id": favorite.id,
            "favorite_type": favorite.favorite_type,
            "object_id": favorite.object_id,
            "created_at": favorite.created_at.isoformat(),
        }
    else:
        payload = favorite.copy()
    return {**payload, "item": _favorite_item(favorite)}


def _favorite_queryset(request):
    user = _django_user(request)
    if user.is_authenticated:
        return Favorite.objects.filter(user=user)
    return Favorite.objects.filter(user__isnull=True, client_id=_client_id(request))


@extend_schema(
    methods=["GET"],
    tags=[TAGS["profile"]],
    summary="사용자 청약 조건 조회",
    description="로그인 사용자는 저장된 UserProfile을, 비로그인 사용자는 세션 프로필을 반환합니다.",
    responses={200: PROFILE_RESPONSE},
)
@extend_schema(
    methods=["PUT"],
    tags=[TAGS["profile"]],
    summary="사용자 청약 조건 저장",
    description="청약 추천, 자금 로드맵, AI 코치가 함께 사용하는 사용자 조건을 저장합니다.",
    request=PROFILE_RESPONSE,
    responses={200: PROFILE_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET", "PUT"])
def profile_view(request):
    user = _django_user(request)
    if user.is_authenticated:
        profile = _profile_for_user(user)
        if request.method == "PUT":
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)
            serializer.save()
            return Response(serializer.data)
        return Response(_profile_payload(profile))

    profile = request.session.get("profile", default_profile())
    if request.method == "PUT":
        profile.update(request.data)
        request.session["profile"] = profile
    return Response(profile)


@extend_schema(
    methods=["GET"],
    tags=[TAGS["profile"]],
    summary="관심 항목 목록 조회",
    description="관심 공고, 관심 주택형 옵션, 관심 금융상품, 관심 정책을 최근 저장순으로 반환합니다.",
    parameters=[CLIENT_ID_HEADER],
    responses={200: FAVORITE_LIST_RESPONSE},
)
@extend_schema(
    methods=["POST"],
    tags=[TAGS["profile"]],
    summary="관심 항목 저장",
    description="로그인 사용자는 계정에, 비로그인 사용자는 X-FirstHome-Client-Id 또는 세션에 관심 항목을 저장합니다.",
    parameters=[CLIENT_ID_HEADER],
    request=FAVORITE_REQUEST,
    responses={201: FAVORITE_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@extend_schema(
    methods=["DELETE"],
    tags=[TAGS["profile"]],
    summary="관심 항목 삭제",
    description="favorite_type과 object_id가 일치하는 관심 항목을 삭제합니다.",
    parameters=[CLIENT_ID_HEADER],
    request=FAVORITE_REQUEST,
    responses={204: None, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET", "POST", "DELETE"])
def favorites_view(request):
    if request.method == "GET":
        favorites = _favorite_queryset(request).order_by("-created_at", "-id")
        return Response([_serialize_favorite(favorite) for favorite in favorites])

    favorite_type = request.data.get("favorite_type")
    object_id = request.data.get("object_id")
    if favorite_type not in {"notice", "option", "product", "policy"} or object_id is None:
        return Response({"detail": "favorite_type and object_id are required"}, status=400)

    favorite_payload = {
        "favorite_type": favorite_type,
        "object_id": int(object_id),
    }

    if request.method == "POST":
        lookup = favorite_payload.copy()
        user = _django_user(request)
        if user.is_authenticated:
            lookup["user"] = user
            lookup["client_id"] = None
        else:
            lookup["user"] = None
            lookup["client_id"] = _client_id(request)

        favorite, _created = Favorite.objects.get_or_create(**lookup)
        return Response(_serialize_favorite(favorite), status=201)

    _favorite_queryset(request).filter(**favorite_payload).delete()
    return Response(status=204)


@extend_schema(
    tags=[TAGS["auth"]],
    summary="현재 로그인 사용자 조회",
    description="현재 세션의 사용자, 프로필, 계정 상태를 반환합니다. 비로그인 상태에서는 is_authenticated=false를 반환합니다.",
    responses={200: AUTH_RESPONSE},
)
@api_view(["GET"])
def auth_me_view(request):
    user = _django_user(request)
    payload = {"user": _serialize_user(user)}
    if user.is_authenticated:
        payload["profile"] = _profile_payload(_profile_for_user(user))
        payload["account_state"] = _account_state_payload(_state_for_user(user))
    else:
        payload["account_state"] = _session_account_state(request)
    return Response(payload)


@extend_schema(
    tags=[TAGS["auth"]],
    summary="회원가입",
    description="사용자 계정을 생성하고 즉시 로그인 처리합니다. 세션/클라이언트에 있던 프로필과 관심 항목을 계정으로 병합합니다.",
    request=AUTH_REQUEST,
    responses={201: AUTH_RESPONSE, 400: ERROR_RESPONSE},
)
@api_view(["POST"])
def register_view(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    email = str(request.data.get("email", "")).strip()
    if not username or not password:
        return Response({"detail": "username and password are required"}, status=400)
    if len(password) < 8:
        return Response({"detail": "password must be at least 8 characters"}, status=400)

    try:
        User = get_user_model()
        user = User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        return Response({"detail": "username already exists"}, status=400)

    _profile_for_user(user)
    login(request._request, user)
    _merge_session_profile(request, user)
    _merge_session_account_state(request, user)
    _merge_client_favorites(request, user)
    return Response(
        {
            "user": _serialize_user(user),
            "profile": _profile_payload(_profile_for_user(user)),
            "account_state": _account_state_payload(_state_for_user(user)),
        },
        status=201,
    )


@extend_schema(
    tags=[TAGS["auth"]],
    summary="로그인",
    description="아이디와 비밀번호로 로그인하고 세션/클라이언트 관심 항목을 계정으로 병합합니다.",
    request=AUTH_REQUEST,
    responses={200: AUTH_RESPONSE, 400: ERROR_RESPONSE},
)
@api_view(["POST"])
def login_view(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    user = authenticate(request._request, username=username, password=password)
    if user is None:
        return Response({"detail": "invalid username or password"}, status=400)

    login(request._request, user)
    _merge_session_profile(request, user)
    _merge_session_account_state(request, user)
    _merge_client_favorites(request, user)
    return Response(
        {
            "user": _serialize_user(user),
            "profile": _profile_payload(_profile_for_user(user)),
            "account_state": _account_state_payload(_state_for_user(user)),
        }
    )


@extend_schema(
    tags=[TAGS["auth"]],
    summary="로그아웃",
    description="현재 세션을 로그아웃 처리합니다.",
    request=None,
    responses={200: LOGOUT_RESPONSE},
)
@api_view(["POST"])
def logout_view(request):
    logout(request._request)
    return Response({"user": {"is_authenticated": False}})


@extend_schema(
    methods=["GET"],
    tags=[TAGS["profile"]],
    summary="현재 선택 상태 조회",
    description="사용자가 마지막으로 선택한 공고, 주택형 옵션, 추천 스냅샷, 자금 로드맵 상태를 반환합니다.",
    responses={200: ACCOUNT_STATE_RESPONSE},
)
@extend_schema(
    methods=["PUT"],
    tags=[TAGS["profile"]],
    summary="현재 선택 상태 저장",
    description="대시보드, 상세, 자금 로드맵, AI 코치 화면 간에 공유되는 선택 상태를 저장합니다.",
    request=ACCOUNT_STATE_REQUEST,
    responses={200: ACCOUNT_STATE_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET", "PUT"])
def account_state_view(request):
    user = _django_user(request)
    if user.is_authenticated:
        state = _state_for_user(user)
        if request.method == "PUT":
            _update_account_state_from_payload(state, request.data)
        return Response(_account_state_payload(state))

    session_state = _session_account_state(request)
    if request.method == "PUT":
        session_state.update(_account_state_payload(request.data))
        request.session["account_state"] = session_state
    return Response(session_state)
