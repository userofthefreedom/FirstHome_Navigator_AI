from __future__ import annotations

from apps.fixture_store import default_profile
from apps.profiles.models import UserProfile
from apps.profiles.serializers import UserProfileSerializer


PROFILE_FIELDS = [
    "name",
    "birth_year",
    "job_status",
    "annual_income",
    "asset",
    "debt",
    "monthly_saving",
    "is_homeless",
    "subscription_months",
    "special_conditions",
    "preferred_regions",
    "preferred_supply_types",
    "target_months",
]


def django_user(request):
    raw_request = getattr(request, "_request", request)
    return getattr(raw_request, "user", None)


def profile_defaults() -> dict:
    profile = default_profile()
    return {field: profile.get(field) for field in PROFILE_FIELDS}


def user_profile(user) -> UserProfile:
    profile, _created = UserProfile.objects.get_or_create(user=user, defaults=profile_defaults())
    return profile


def profile_payload(profile: UserProfile) -> dict:
    return UserProfileSerializer(profile).data


def profile_from_request(request) -> dict:
    user = django_user(request)
    if user and user.is_authenticated:
        return profile_payload(user_profile(user))
    return request.session.get("profile", default_profile())
