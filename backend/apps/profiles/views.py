from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.services import default_profile


@api_view(["GET", "PUT"])
def profile_view(request):
    profile = request.session.get("profile", default_profile())
    if request.method == "PUT":
        profile.update(request.data)
        request.session["profile"] = profile
    return Response(profile)
