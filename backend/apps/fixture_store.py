from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError


FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "firsthome_mvp.json"


@lru_cache(maxsize=1)
def load_fixture() -> dict[str, Any]:
    with Path(FIXTURE_PATH).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def default_profile() -> dict[str, Any]:
    return load_fixture()["profile"].copy()


def sample_profiles() -> list[dict[str, Any]]:
    return [profile.copy() for profile in load_fixture().get("sample_profiles", [])]


def notices() -> list[dict[str, Any]]:
    db_notices = _db_notices()
    if db_notices:
        return db_notices
    return [notice.copy() for notice in load_fixture()["notices"]]


def products() -> list[dict[str, Any]]:
    db_products = _db_products()
    if db_products:
        return db_products
    return [product.copy() for product in load_fixture()["products"]]


def policies() -> list[dict[str, Any]]:
    db_policies = _db_policies()
    if db_policies:
        return db_policies
    return [policy.copy() for policy in load_fixture()["policies"]]


def find_notice(notice_id: int) -> dict[str, Any] | None:
    return next((notice for notice in notices() if notice["id"] == notice_id), None)


def _db_notices() -> list[dict[str, Any]]:
    try:
        from apps.notices.models import HousingNotice

        return [_serialize_notice(notice) for notice in HousingNotice.objects.order_by("application_deadline", "id")]
    except (OperationalError, ProgrammingError):
        return []


def _db_products() -> list[dict[str, Any]]:
    try:
        from apps.products.models import FinancialProduct

        return [_serialize_product(product) for product in FinancialProduct.objects.order_by("term_months", "-protection_status", "id")]
    except (OperationalError, ProgrammingError):
        return []


def _db_policies() -> list[dict[str, Any]]:
    try:
        from apps.policies.models import YouthPolicy

        return [_serialize_policy(policy) for policy in YouthPolicy.objects.order_by("policy_category", "id")]
    except (OperationalError, ProgrammingError):
        return []


def _date_value(value: Any) -> str:
    return value.isoformat() if value else ""


def _money_limit(value: int) -> str:
    return "제한 없음" if not value else f"월 {round(value / 10000):,}만원"


def _term_label(value: int) -> str:
    return "상시" if value <= 1 else f"{value}개월"


def _serialize_notice(notice: Any) -> dict[str, Any]:
    return {
        "id": notice.id,
        "title": notice.title,
        "provider": notice.provider,
        "region": notice.region,
        "district": notice.district,
        "supply_type": notice.supply_type,
        "housing_type": notice.housing_type,
        "area": notice.area,
        "price": notice.price,
        "contract_rate": notice.contract_rate,
        "application_deadline": _date_value(notice.application_deadline),
        "winner_date": _date_value(notice.winner_date),
        "contract_date": _date_value(notice.contract_date),
        "move_in": notice.move_in,
        "competition": notice.competition,
        "source_url": notice.source_url,
        "tags": notice.tags,
        "required_documents": notice.required_documents,
        "cautions": notice.cautions,
    }


def _serialize_product(product: Any) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "provider": product.provider,
        "category": product.category,
        "rate": product.rate,
        "limit": _money_limit(product.monthly_limit),
        "period": _term_label(product.term_months),
        "term_months": product.term_months,
        "monthly_limit": product.monthly_limit,
        "protection_status": product.protection_status,
        "source_url": product.source_url,
        "reasons": product.reasons,
    }


def _serialize_policy(policy: Any) -> dict[str, Any]:
    return {
        "id": policy.id,
        "name": policy.name,
        "provider": policy.provider,
        "target": policy.target,
        "benefit": policy.benefit,
        "policy_category": policy.policy_category,
        "regions": policy.regions,
        "age_min": policy.age_min,
        "age_max": policy.age_max,
        "max_income": policy.max_income,
        "requires_homeless": policy.requires_homeless,
        "source_url": policy.source_url,
        "reasons": policy.reasons,
    }
