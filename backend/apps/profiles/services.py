from __future__ import annotations

from apps.fixture_store import default_profile
from apps.profiles.models import UserAccountState, UserProfile
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
    "desired_area_min_m2",
    "desired_area_max_m2",
    "desired_price_min",
    "desired_price_max",
    "max_down_payment",
    "monthly_payment_capacity",
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


def user_account_state(user) -> UserAccountState:
    state, _created = UserAccountState.objects.get_or_create(user=user)
    return state


def profile_payload(profile: UserProfile) -> dict:
    return UserProfileSerializer(profile).data


def profile_is_default_like(payload: dict) -> bool:
    defaults = profile_defaults()
    return all(payload.get(field) in (defaults.get(field), None, "", []) for field in PROFILE_FIELDS)


def account_state_payload(state: UserAccountState | dict | None) -> dict:
    if state is None:
        return {
            "current_notice_id": None,
            "current_option_id": None,
            "last_recommendations": [],
            "last_funding_plan": {},
        }
    if isinstance(state, dict):
        return {
            "current_notice_id": _positive_or_none(state.get("current_notice_id") or state.get("noticeId")),
            "current_option_id": _positive_or_none(state.get("current_option_id") or state.get("optionId")),
            "last_recommendations": state.get("last_recommendations") or [],
            "last_funding_plan": state.get("last_funding_plan") or {},
        }
    return {
        "current_notice_id": state.current_notice_id,
        "current_option_id": state.current_option_id,
        "last_recommendations": state.last_recommendations or [],
        "last_funding_plan": state.last_funding_plan or {},
        "updated_at": state.updated_at.isoformat() if state.updated_at else "",
    }


def update_account_state_from_payload(state: UserAccountState, payload: dict, *, save: bool = True) -> UserAccountState:
    if "current_notice_id" in payload or "noticeId" in payload:
        state.current_notice_id = _positive_or_none(payload.get("current_notice_id") or payload.get("noticeId"))
    if "current_option_id" in payload or "optionId" in payload:
        state.current_option_id = _positive_or_none(payload.get("current_option_id") or payload.get("optionId"))
    if "last_recommendations" in payload and isinstance(payload.get("last_recommendations"), list):
        state.last_recommendations = payload["last_recommendations"]
    if "last_funding_plan" in payload and isinstance(payload.get("last_funding_plan"), dict):
        state.last_funding_plan = payload["last_funding_plan"]
    if save:
        state.save()
    return state


def _positive_or_none(value) -> int | None:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def profile_from_request(request) -> dict:
    user = django_user(request)
    if user and user.is_authenticated:
        return profile_payload(user_profile(user))
    return request.session.get("profile", default_profile())


def save_last_recommendations(request, recommendations: list[dict]) -> None:
    snapshot = _recommendation_snapshot(recommendations)
    user = django_user(request)
    if user and user.is_authenticated:
        state = user_account_state(user)
        changed_fields = []
        if state.last_recommendations != snapshot:
            state.last_recommendations = snapshot
            changed_fields.append("last_recommendations")
        if recommendations and not state.current_notice_id:
            first = recommendations[0]
            state.current_notice_id = _positive_or_none(first.get("notice_id"))
            best_option = first.get("best_option") if isinstance(first.get("best_option"), dict) else {}
            state.current_option_id = _positive_or_none(best_option.get("option_id"))
            changed_fields.extend(["current_notice_id", "current_option_id"])
        if changed_fields:
            state.save(update_fields=[*dict.fromkeys(changed_fields), "updated_at"])
        return

    session_state = account_state_payload(request.session.get("account_state", {}))
    changed = session_state.get("last_recommendations") != snapshot
    session_state["last_recommendations"] = snapshot
    if recommendations and not session_state.get("current_notice_id"):
        first = recommendations[0]
        session_state["current_notice_id"] = _positive_or_none(first.get("notice_id"))
        best_option = first.get("best_option") if isinstance(first.get("best_option"), dict) else {}
        session_state["current_option_id"] = _positive_or_none(best_option.get("option_id"))
        changed = True
    if changed:
        request.session["account_state"] = session_state


def _recommendation_snapshot(recommendations: list[dict]) -> list[dict]:
    snapshot = []
    for item in recommendations[:6]:
        best_option = item.get("best_option") if isinstance(item.get("best_option"), dict) else {}
        snapshot.append(
            {
                "notice_id": _positive_or_none(item.get("notice_id")),
                "option_id": _positive_or_none(best_option.get("option_id")),
                "score": item.get("total_score"),
                "title": item.get("title", ""),
            }
        )
    return snapshot
