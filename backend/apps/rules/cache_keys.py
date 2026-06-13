from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Max


PROFILE_SCORE_FIELDS = (
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
)


def stable_hash(value: Any, *, length: int = 20) -> str:
    payload = json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def profile_hash(profile: dict[str, Any]) -> str:
    return stable_hash({field: profile.get(field) for field in PROFILE_SCORE_FIELDS})


def data_version() -> str:
    parts: list[Any] = []
    for model_path in (
        "apps.notices.models.HousingNotice",
        "apps.notice_docs.models.HousingUnitOption",
        "apps.notice_docs.models.PaymentSchedule",
        "apps.products.models.FinancialProduct",
        "apps.products.models.LoanProduct",
        "apps.policies.models.YouthPolicy",
    ):
        parts.append(_model_version(model_path))
    parts.append(_fixture_version())
    return stable_hash(parts, length=16)


def cache_key(namespace: str, *parts: Any) -> str:
    return f"firsthome:{namespace}:{stable_hash(parts, length=28)}"


def _model_version(model_path: str) -> dict[str, Any]:
    module_name, class_name = model_path.rsplit(".", 1)
    try:
        module = __import__(module_name, fromlist=[class_name])
        model = getattr(module, class_name)
        try:
            model._meta.get_field("updated_at")
            aggregate = model.objects.aggregate(updated=Max("updated_at"))
            updated = aggregate.get("updated")
        except FieldDoesNotExist:
            updated = None
        return {
            "model": model_path,
            "count": model.objects.count(),
            "max_id": model.objects.order_by("-id").values_list("id", flat=True).first() or 0,
            "updated": updated.isoformat() if updated else "",
        }
    except (OperationalError, ProgrammingError):
        return {"model": model_path, "unavailable": True}


def _fixture_version() -> dict[str, Any]:
    path = Path(settings.BASE_DIR) / "fixtures" / "firsthome_mvp.json"
    try:
        stat = path.stat()
    except OSError:
        return {"fixture": "", "missing": True}
    return {"fixture": str(path), "mtime": stat.st_mtime, "size": stat.st_size}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, (list, tuple, set)):
        normalized = [_normalize(item) for item in value]
        if isinstance(value, set):
            return sorted(normalized, key=str)
        return normalized
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
