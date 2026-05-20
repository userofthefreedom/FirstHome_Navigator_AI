from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.profiles.models import Favorite
from apps.services import default_profile, find_notice, policies, products


def _client_id(request) -> str:
    header_value = request.headers.get("X-FirstHome-Client-Id", "").strip()
    if header_value:
        return header_value[:64]

    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or "anonymous"


def _favorite_item(favorite: Favorite | dict) -> dict | None:
    favorite_type = favorite.favorite_type if isinstance(favorite, Favorite) else favorite["favorite_type"]
    object_id = int(favorite.object_id if isinstance(favorite, Favorite) else favorite["object_id"])
    if favorite_type == "notice":
        return find_notice(object_id)
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
    if request.user.is_authenticated:
        return Favorite.objects.filter(user=request.user)
    return Favorite.objects.filter(user__isnull=True, client_id=_client_id(request))


@api_view(["GET", "PUT"])
def profile_view(request):
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
    if favorite_type not in {"notice", "product", "policy"} or object_id is None:
        return Response({"detail": "favorite_type and object_id are required"}, status=400)

    favorite_payload = {
        "favorite_type": favorite_type,
        "object_id": int(object_id),
    }

    if request.method == "POST":
        lookup = favorite_payload.copy()
        if request.user.is_authenticated:
            lookup["user"] = request.user
        else:
            lookup["user"] = None
            lookup["client_id"] = _client_id(request)

        favorite, _created = Favorite.objects.get_or_create(**lookup)
        return Response(_serialize_favorite(favorite), status=201)

    _favorite_queryset(request).filter(**favorite_payload).delete()
    return Response(status=204)
