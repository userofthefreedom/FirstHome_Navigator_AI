from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError

from apps.notices.services.classifier import classify_notice_payload
from apps.notice_docs.services.status import fixture_analysis_summary, notice_analysis_summary


FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "firsthome_mvp.json"


@lru_cache(maxsize=1)
def load_fixture() -> dict[str, Any]:
    with Path(FIXTURE_PATH).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def default_profile() -> dict[str, Any]:
    return load_fixture()["profile"].copy()


def sample_profiles() -> list[dict[str, Any]]:
    return [profile.copy() for profile in load_fixture().get("sample_profiles", [])]


def notices(
    *,
    include_excluded: bool = False,
    region: str | None = None,
    ownership_type: str | None = None,
) -> list[dict[str, Any]]:
    db_notices = _db_notices()
    fixture_notices = [_fixture_notice(notice) for notice in load_fixture()["notices"]]
    items = _notices_with_fixture_supplement(db_notices, fixture_notices)
    return _filter_notices(items, include_excluded=include_excluded, region=region, ownership_type=ownership_type)


def products() -> list[dict[str, Any]]:
    db_products = _db_products()
    if db_products:
        return db_products
    return [_fixture_product(product) for product in load_fixture()["products"]]


def policies() -> list[dict[str, Any]]:
    db_policies = _db_policies()
    if db_policies:
        return db_policies
    return [_fixture_policy(policy) for policy in load_fixture()["policies"]]


def find_notice(notice_id: int) -> dict[str, Any] | None:
    return next((notice for notice in notices(include_excluded=True) if notice["id"] == notice_id), None)


def _db_notices() -> list[dict[str, Any]]:
    try:
        from apps.notices.models import HousingNotice

        return [_serialize_notice(notice) for notice in HousingNotice.objects.order_by("application_deadline", "id")]
    except (OperationalError, ProgrammingError):
        return []


def _fixture_notice(notice: dict[str, Any]) -> dict[str, Any]:
    classification = classify_notice_payload(notice)
    payload = {
        **notice.copy(),
        "source_id": str(notice.get("id", "")),
        "data_source": "fixture",
        "is_price_confirmed": int(notice.get("price") or 0) > 0,
        "source_meta": {},
        "ownership_type": notice.get("ownership_type") or classification.ownership_type,
        "is_service_target": notice.get("is_service_target", classification.is_service_target),
        "exclude_reason": notice.get("exclude_reason", classification.exclude_reason),
        "official_document_status": notice.get("official_document_status", classification.official_document_status),
        "document_count": int(notice.get("document_count", 0) or 0),
        "unit_option_count": int(notice.get("unit_option_count", 0) or 0),
    }
    return {**payload, "analysis_summary": fixture_analysis_summary(payload)}


def _notices_with_fixture_supplement(
    db_notices: list[dict[str, Any]],
    fixture_notices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not db_notices:
        return fixture_notices

    fallback_settings = getattr(settings, "FIRSTHOME_FIXTURE_FALLBACK", {})
    if not fallback_settings.get("ENABLE_SUPPLEMENT", True):
        return db_notices

    min_service_notices = int(fallback_settings.get("MIN_SERVICE_NOTICES", 3) or 0)
    if min_service_notices <= 0:
        return db_notices

    db_service_count = sum(1 for notice in db_notices if notice.get("is_service_target"))
    if db_service_count >= min_service_notices:
        return db_notices

    existing_ids = {str(notice.get("id")) for notice in db_notices}
    existing_source_ids = {str(notice.get("source_id")) for notice in db_notices if notice.get("source_id")}
    needed = min_service_notices - db_service_count
    supplements: list[dict[str, Any]] = []
    for notice in fixture_notices:
        if not notice.get("is_service_target"):
            continue
        if str(notice.get("id")) in existing_ids or str(notice.get("source_id")) in existing_source_ids:
            continue
        supplements.append({**notice, "data_source": "fixture fallback"})
        if len(supplements) >= needed:
            break
    return [*db_notices, *supplements]


def _fixture_product(product: dict[str, Any]) -> dict[str, Any]:
    return {**product.copy(), "data_source": "fixture"}


def _fixture_policy(policy: dict[str, Any]) -> dict[str, Any]:
    return {**policy.copy(), "data_source": "fixture"}


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
    payload = {
        "id": notice.id,
        "source_id": notice.source_id,
        "data_source": _notice_data_source(notice),
        "is_price_confirmed": notice.price > 0,
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
        "source_meta": notice.source_meta,
        "ownership_type": getattr(notice, "ownership_type", "unknown"),
        "is_service_target": getattr(notice, "is_service_target", False),
        "exclude_reason": getattr(notice, "exclude_reason", ""),
        "official_document_status": getattr(notice, "official_document_status", "not_requested"),
        "document_count": _related_count(notice, "documents"),
        "unit_option_count": _related_count(notice, "unit_options"),
    }
    classification = classify_notice_payload(payload)
    if payload["ownership_type"] == "unknown":
        payload["ownership_type"] = classification.ownership_type
    if payload["ownership_type"] in {"unknown", "excluded"} or not payload["is_service_target"]:
        payload["is_service_target"] = classification.is_service_target
    if not payload["exclude_reason"]:
        payload["exclude_reason"] = classification.exclude_reason
    payload["analysis_summary"] = notice_analysis_summary(notice)
    return payload


def _related_count(instance: Any, related_name: str) -> int:
    manager = getattr(instance, related_name, None)
    if manager is None:
        return 0
    try:
        return manager.count()
    except (OperationalError, ProgrammingError, AttributeError):
        return 0


def _filter_notices(
    items: list[dict[str, Any]],
    *,
    include_excluded: bool,
    region: str | None,
    ownership_type: str | None,
) -> list[dict[str, Any]]:
    filtered = items
    if not include_excluded:
        filtered = [notice for notice in filtered if notice.get("is_service_target")]
    if ownership_type:
        normalized = "public_sale" if ownership_type in {"service_target", "sale"} else ownership_type
        filtered = [
            notice
            for notice in filtered
            if notice.get("ownership_type") == normalized
            or (normalized == "public_sale" and notice.get("is_service_target"))
        ]
    if region:
        filtered = [notice for notice in filtered if notice.get("region") == region]
    return filtered


def _serialize_product(product: Any) -> dict[str, Any]:
    return {
        "id": product.id,
        "data_source": _product_data_source(product),
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
        "data_source": _policy_data_source(policy),
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


def _notice_data_source(notice: Any) -> str:
    if notice.provider == "LH" and notice.source_id and not str(notice.source_id).isdigit():
        return "LH API"
    if notice.source_id:
        return "DB"
    return "fixture"


def _product_data_source(product: Any) -> str:
    if "finlife.fss.or.kr" in (product.source_url or ""):
        return "금융감독원 API"
    return "DB"


def _policy_data_source(policy: Any) -> str:
    if any("온통청년" in str(reason) for reason in (policy.reasons or [])):
        return "온통청년 API"
    if "youthcenter.go.kr" in (policy.source_url or ""):
        return "온통청년 API"
    if policy.source_url:
        return "정책 데이터"
    return "DB"
