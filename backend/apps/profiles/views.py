from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.fixture_store import default_profile, find_notice, policies, products
from apps.notice_docs.models import HousingUnitOption
from apps.notice_docs.serializers import serialize_unit_option
from apps.profiles.models import Favorite, UserProfile
from apps.profiles.serializers import UserProfileSerializer
from apps.profiles.services import (
    PROFILE_FIELDS,
    django_user as _django_user,
    profile_defaults as _profile_defaults,
    profile_payload as _profile_payload,
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
    for field in PROFILE_FIELDS:
        if field in session_profile:
            setattr(profile, field, session_profile[field])
    profile.save()


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
        return find_notice(object_id)
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


@api_view(["GET"])
def auth_me_view(request):
    user = _django_user(request)
    payload = {"user": _serialize_user(user)}
    if user.is_authenticated:
        payload["profile"] = _profile_payload(_profile_for_user(user))
    return Response(payload)


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
        user = User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        return Response({"detail": "username already exists"}, status=400)

    _profile_for_user(user)
    login(request._request, user)
    _merge_session_profile(request, user)
    _merge_client_favorites(request, user)
    return Response({"user": _serialize_user(user), "profile": _profile_payload(_profile_for_user(user))}, status=201)


@api_view(["POST"])
def login_view(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    user = authenticate(request._request, username=username, password=password)
    if user is None:
        return Response({"detail": "invalid username or password"}, status=400)

    login(request._request, user)
    _merge_session_profile(request, user)
    _merge_client_favorites(request, user)
    return Response({"user": _serialize_user(user), "profile": _profile_payload(_profile_for_user(user))})


@api_view(["POST"])
def logout_view(request):
    logout(request._request)
    return Response({"user": {"is_authenticated": False}})
