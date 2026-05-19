from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.services import default_profile, find_notice, policies, products


def _favorites(request) -> list[dict]:
    return list(request.session.get("favorites", []))


def _favorite_item(favorite: dict) -> dict | None:
    object_id = int(favorite["object_id"])
    if favorite["favorite_type"] == "notice":
        return find_notice(object_id)
    if favorite["favorite_type"] == "product":
        return next((product for product in products() if product["id"] == object_id), None)
    if favorite["favorite_type"] == "policy":
        return next((policy for policy in policies() if policy["id"] == object_id), None)
    return None


def _serialize_favorite(favorite: dict) -> dict:
    return {**favorite, "item": _favorite_item(favorite)}


@api_view(["GET", "PUT"])
def profile_view(request):
    profile = request.session.get("profile", default_profile())
    if request.method == "PUT":
        profile.update(request.data)
        request.session["profile"] = profile
    return Response(profile)


@api_view(["GET", "POST", "DELETE"])
def favorites_view(request):
    favorites = _favorites(request)

    if request.method == "GET":
        return Response([_serialize_favorite(favorite) for favorite in favorites])

    favorite_type = request.data.get("favorite_type")
    object_id = request.data.get("object_id")
    if favorite_type not in {"notice", "product", "policy"} or object_id is None:
        return Response({"detail": "favorite_type and object_id are required"}, status=400)

    next_favorite = {"favorite_type": favorite_type, "object_id": int(object_id)}

    if request.method == "POST":
        if next_favorite not in favorites:
            favorites.append(next_favorite)
            request.session["favorites"] = favorites
        return Response(_serialize_favorite(next_favorite), status=201)

    request.session["favorites"] = [favorite for favorite in favorites if favorite != next_favorite]
    return Response(status=204)
