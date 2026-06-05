from __future__ import annotations

import json
import threading
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import OperationalError, ProgrammingError, transaction

from apps.notices.services.classifier import classify_notice_payload
from apps.notices.services.map_locations import resolve_notice_location
from apps.notice_docs.services.status import fixture_analysis_summary, notice_analysis_summary


FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "firsthome_mvp.json"
METROPOLITAN_REGIONS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
)
_FIXTURE_MATERIALIZE_LOCK = threading.RLock()


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


def current_notices(
    *,
    include_excluded: bool = False,
    region: str | None = None,
    ownership_type: str | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    return [
        notice
        for notice in notices(include_excluded=include_excluded, region=region, ownership_type=ownership_type)
        if is_current_notice(notice, today=today)
    ]


def is_current_notice(notice: dict[str, Any], *, today: date | None = None) -> bool:
    deadline = _notice_deadline_date(notice)
    if deadline is None:
        return False
    return deadline >= (today or date.today())


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

        items = [_serialize_notice(notice) for notice in HousingNotice.objects.order_by("application_deadline", "id")]
        return sorted(items, key=lambda item: (_is_fixture_notice(item), item.get("application_deadline") or "", item["id"]))
    except (OperationalError, ProgrammingError):
        return []


def _fixture_notice(notice: dict[str, Any]) -> dict[str, Any]:
    classification = classify_notice_payload(notice)
    location = resolve_notice_location(notice)
    payload = {
        **notice.copy(),
        "source_id": str(notice.get("id", "")),
        "data_source": "fixture",
        "is_price_confirmed": int(notice.get("price") or 0) > 0,
        "source_meta": {"fixture_id": notice.get("id"), "fixture_notice": True},
        "ownership_type": notice.get("ownership_type") or classification.ownership_type,
        "is_service_target": notice.get("is_service_target", classification.is_service_target),
        "exclude_reason": notice.get("exclude_reason", classification.exclude_reason),
        "official_document_status": notice.get("official_document_status", classification.official_document_status),
        "document_count": int(notice.get("document_count", 0) or 0),
        "unit_option_count": int(notice.get("unit_option_count", 0) or 0),
        "location_label": notice.get("location_label") or location["label"],
        "latitude": notice.get("latitude") or location["lat"],
        "longitude": notice.get("longitude") or location["lng"],
        "geocode_quality": notice.get("geocode_quality") or location["quality"],
    }
    return {**payload, "analysis_summary": fixture_analysis_summary(payload)}


def _notices_with_fixture_supplement(
    db_notices: list[dict[str, Any]],
    fixture_notices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fallback_settings = getattr(settings, "FIRSTHOME_FIXTURE_FALLBACK", {})
    if not fallback_settings.get("ENABLE_SUPPLEMENT", True):
        return db_notices or fixture_notices

    min_per_region = int(
        fallback_settings.get(
            "MIN_ACTIVE_SERVICE_NOTICES_PER_REGION",
            fallback_settings.get("MIN_SERVICE_NOTICES", 5),
        )
        or 0
    )
    if min_per_region <= 0:
        return db_notices or fixture_notices

    with _FIXTURE_MATERIALIZE_LOCK:
        latest_db_notices = _db_notices()
        if _materialize_fixture_supplements(latest_db_notices, fixture_notices, min_per_region=min_per_region):
            return _db_notices()

    return latest_db_notices or db_notices or fixture_notices


def _materialize_fixture_supplements(
    db_notices: list[dict[str, Any]],
    fixture_notices: list[dict[str, Any]],
    *,
    min_per_region: int,
) -> bool:
    try:
        from apps.notices.models import HousingNotice
    except (OperationalError, ProgrammingError):
        return False

    changed = _sync_existing_fixture_notices(fixture_notices)
    actual_counts = {region: 0 for region in METROPOLITAN_REGIONS}
    fixture_counts = {region: 0 for region in METROPOLITAN_REGIONS}
    for notice in db_notices:
        if not notice.get("is_service_target") or not is_current_notice(notice):
            continue
        region_key = _metropolitan_region(notice)
        if region_key not in actual_counts:
            continue
        if _is_fixture_notice(notice):
            fixture_counts[region_key] += 1
        else:
            actual_counts[region_key] += 1

    for region in METROPOLITAN_REGIONS:
        needed = max(0, min_per_region - actual_counts[region] - fixture_counts[region])
        if needed <= 0:
            continue
        candidates = [
            notice
            for notice in fixture_notices
            if notice.get("is_service_target")
            and is_current_notice(notice)
            and _metropolitan_region(notice) == region
        ]
        for notice in candidates[:needed]:
            if _materialize_fixture_notice(notice):
                changed = True

    return changed


def _sync_existing_fixture_notices(fixture_notices: list[dict[str, Any]]) -> bool:
    from apps.notices.models import HousingNotice

    changed = False
    fixture_by_id = {int(notice["id"]): notice for notice in fixture_notices if notice.get("id")}
    existing_notices = HousingNotice.objects.filter(source_meta__fixture_id__in=fixture_by_id.keys())
    for existing in existing_notices:
        fixture_id = int(existing.source_meta.get("fixture_id"))
        fixture_notice = fixture_by_id.get(fixture_id)
        if fixture_notice and _fixture_notice_is_stale(existing, fixture_notice):
            _materialize_fixture_notice(fixture_notice)
            changed = True
    return changed


def _fixture_notice_is_stale(existing: Any, notice: dict[str, Any]) -> bool:
    fixture_id = int(notice["id"])
    location = resolve_notice_location(notice)
    expected_fields = {
        "source_id": f"fixture-{fixture_id}",
        "title": notice["title"],
        "region": notice["region"],
        "district": notice["district"],
        "supply_type": notice["supply_type"],
        "housing_type": notice["housing_type"],
        "area": notice.get("area", ""),
        "price": int(notice.get("price", 0) or 0),
        "application_deadline": _parse_iso_date(notice.get("application_deadline")),
        "winner_date": _parse_iso_date(notice.get("winner_date")),
        "contract_date": _parse_iso_date(notice.get("contract_date")),
        "move_in": notice.get("move_in", ""),
        "source_url": "",
        "location_label": notice.get("location_label") or location["label"],
        "latitude": Decimal(str(notice.get("latitude") or location["lat"])),
        "longitude": Decimal(str(notice.get("longitude") or location["lng"])),
        "geocode_quality": notice.get("geocode_quality") or location["quality"],
    }
    return any(getattr(existing, key) != value for key, value in expected_fields.items())


def _materialize_fixture_notice(notice: dict[str, Any]) -> bool:
    from apps.notices.models import HousingNotice

    fixture_id = int(notice["id"])
    source_id = f"fixture-{fixture_id}"
    existing = HousingNotice.objects.filter(source_meta__fixture_id=fixture_id).first()
    if existing is None:
        existing = HousingNotice.objects.filter(source_id=source_id).first()
    if existing is not None and not _fixture_notice_is_stale(existing, notice) and _fixture_analysis_is_seeded(existing, notice):
        return False

    classification = classify_notice_payload(notice)
    location = resolve_notice_location(notice)
    defaults = {
        "source_id": source_id,
        "title": notice["title"],
        "provider": notice.get("provider", "Fixture"),
        "region": notice["region"],
        "district": notice["district"],
        "supply_type": notice["supply_type"],
        "housing_type": notice["housing_type"],
        "area": notice.get("area", ""),
        "price": int(notice.get("price", 0) or 0),
        "contract_rate": float(notice.get("contract_rate", 0.1) or 0.1),
        "application_deadline": _parse_iso_date(notice.get("application_deadline")),
        "winner_date": _parse_iso_date(notice.get("winner_date")),
        "contract_date": _parse_iso_date(notice.get("contract_date")),
        "move_in": notice.get("move_in", ""),
        "competition": notice.get("competition", ""),
        "source_url": "",
        "location_label": notice.get("location_label") or location["label"],
        "latitude": Decimal(str(notice.get("latitude") or location["lat"])),
        "longitude": Decimal(str(notice.get("longitude") or location["lng"])),
        "geocode_quality": notice.get("geocode_quality") or location["quality"],
        "tags": notice.get("tags", []),
        "required_documents": notice.get("required_documents", []),
        "cautions": notice.get("cautions", []),
        "source_meta": {"fixture_id": fixture_id, "fixture_notice": True},
        "ownership_type": notice.get("ownership_type") or classification.ownership_type,
        "is_service_target": notice.get("is_service_target", classification.is_service_target),
        "exclude_reason": notice.get("exclude_reason", classification.exclude_reason),
        "official_document_status": "analyzed",
    }

    created = False
    if existing is None:
        if not HousingNotice.objects.filter(id=fixture_id).exists():
            existing = HousingNotice.objects.create(id=fixture_id, **defaults)
        else:
            existing = HousingNotice.objects.create(**defaults)
        created = True
    else:
        for key, value in defaults.items():
            setattr(existing, key, value)
        existing.save(update_fields=[*defaults.keys(), "updated_at"])
    seed_fixture_notice_analysis(existing, notice)
    return created


def _fixture_analysis_is_seeded(existing: Any, notice: dict[str, Any]) -> bool:
    try:
        from apps.notice_docs.models import NoticeDocument
    except (OperationalError, ProgrammingError):
        return False

    fixture_id = int(notice["id"])
    expected_option_count = len(notice.get("unit_options", []))
    document_exists = NoticeDocument.objects.filter(
        notice=existing,
        file_id=f"fixture-{fixture_id}",
        status="analyzed",
    ).exists()
    if not document_exists:
        return False
    try:
        return existing.unit_options.count() >= expected_option_count
    except (OperationalError, ProgrammingError, AttributeError):
        return False


def seed_fixture_notice_analysis(notice: Any, fixture_notice: dict[str, Any] | None = None) -> dict[str, Any]:
    from django.utils import timezone

    from apps.notice_docs.models import (
        EligibilityChecklist,
        ExtractionEvidence,
        HousingUnitOption,
        NoticeDocument,
        NoticeExtraction,
        PaymentSchedule,
    )

    fixture_notice = fixture_notice or _fixture_notice_payload_for_model(notice)
    if not fixture_notice:
        return {}

    with transaction.atomic():
        document = NoticeDocument.objects.filter(notice=notice, file_id=f"fixture-{fixture_notice['id']}").first()
        if document is None:
            document = NoticeDocument(notice=notice, file_id=f"fixture-{fixture_notice['id']}")
        document.provider = notice.provider
        document.file_name = f"{fixture_notice['title']}_fixture.pdf"[:220]
        document.document_url = ""
        document.source_url = ""
        document.status = "analyzed"
        document.error_message = ""
        document.analyzed_at = timezone.now()
        document.save()

        extraction = (
            NoticeExtraction.objects.filter(
                notice=notice,
                document=document,
                schema_version="rules-v1",
                raw_json__fixture_id=fixture_notice["id"],
            )
            .order_by("-id")
            .first()
        )
        if extraction is None:
            extraction = NoticeExtraction(notice=notice, document=document, schema_version="rules-v1")
        extraction.status = "valid"
        extraction.confidence = 0.86
        extraction.raw_json = {
            "source": "fixture_rules",
            "fixture_id": fixture_notice["id"],
            "option_count": len(fixture_notice.get("unit_options", [])),
            "required_documents": fixture_notice.get("required_documents", []),
            "status": "valid",
        }
        extraction.save()

        ExtractionEvidence.objects.filter(extraction=extraction).delete()
        kept_option_ids = []
        for option_payload in fixture_notice.get("unit_options", []):
            option, _created = HousingUnitOption.objects.update_or_create(
                notice=notice,
                unit_type=option_payload["unit_type"],
                floor_group=option_payload.get("floor_group", "전체"),
                option_type=option_payload.get("option_type", "general_supply"),
                defaults={
                    "document": document,
                    "extraction": extraction,
                    "exclusive_area_m2": float(option_payload.get("exclusive_area_m2", 0) or 0),
                    "base_price": int(option_payload.get("base_price", 0) or 0),
                    "loan_amount": int(option_payload.get("loan_amount", 0) or 0),
                    "balcony_extension_price": int(option_payload.get("balcony_extension_price", 0) or 0),
                    "confidence": float(option_payload.get("confidence", 0.86) or 0.86),
                    "source_page": int(option_payload.get("source_page", 4) or 4),
                    "source_text": option_payload.get("source_text", "fixture: 발표용 보강 공고의 주택형별 공급금액 표"),
                },
            )
            kept_option_ids.append(option.id)
            option.payment_schedules.all().delete()
            for schedule_payload in option_payload.get("payment_schedules", []):
                PaymentSchedule.objects.create(
                    unit_option=option,
                    label=schedule_payload["label"],
                    due_date=_parse_iso_date(schedule_payload.get("due_date")),
                    amount=int(schedule_payload.get("amount", 0) or 0),
                    payment_type=schedule_payload.get("payment_type", "other"),
                    sequence=int(schedule_payload.get("sequence", 0) or 0),
                    evidence_text=schedule_payload.get("evidence_text", "fixture: 공급금액 및 납부일정 표"),
                )
            ExtractionEvidence.objects.create(
                extraction=extraction,
                field_path=f"unit_options.{option.unit_type}.base_price",
                page_no=option.source_page,
                source_text=option.source_text,
                confidence=option.confidence,
            )

        HousingUnitOption.objects.filter(notice=notice).exclude(id__in=kept_option_ids).delete()
        EligibilityChecklist.objects.filter(notice=notice).delete()
        for row in _fixture_checklist_rows(fixture_notice):
            EligibilityChecklist.objects.create(notice=notice, document=document, **row)

        notice.official_document_status = "analyzed"
        notice.required_documents = fixture_notice.get("required_documents", notice.required_documents)
        notice.save(update_fields=["official_document_status", "required_documents", "updated_at"])
    return {"document": document, "extraction": extraction, "unit_options": list(notice.unit_options.all())}


def _fixture_notice_payload_for_model(notice: Any) -> dict[str, Any] | None:
    source_meta = getattr(notice, "source_meta", {}) or {}
    fixture_id = source_meta.get("fixture_id") if isinstance(source_meta, dict) else None
    if fixture_id is None:
        return None
    for item in load_fixture().get("notices", []):
        if int(item.get("id") or 0) == int(fixture_id):
            return item
    return None


def _fixture_checklist_rows(fixture_notice: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "category": "homeless",
            "title": "무주택 기준 확인",
            "condition_text": "",
            "evidence_text": "fixture: 무주택세대구성원 및 주택소유여부 판정 기준",
            "page_no": 12,
            "confidence": 0.86,
        },
        {
            "category": "income",
            "title": "소득·자산 기준 확인",
            "condition_text": "",
            "evidence_text": "fixture: 공급유형별 소득 및 자산 기준",
            "page_no": 14,
            "confidence": 0.84,
        },
        {
            "category": "residency",
            "title": "지역 우선공급 확인",
            "condition_text": "",
            "evidence_text": f"fixture: {fixture_notice.get('region')} 거주자 우선공급 기준",
            "page_no": 10,
            "confidence": 0.82,
        },
        {
            "category": "subscription",
            "title": "청약통장 요건 확인",
            "condition_text": "",
            "evidence_text": "fixture: 입주자저축 가입기간 및 납입인정 기준",
            "page_no": 18,
            "confidence": 0.84,
        },
    ]


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


def _notice_deadline_date(notice: dict[str, Any]) -> date | None:
    value = notice.get("application_deadline")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


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
        "location_label": getattr(notice, "location_label", ""),
        "latitude": float(notice.latitude) if getattr(notice, "latitude", None) is not None else None,
        "longitude": float(notice.longitude) if getattr(notice, "longitude", None) is not None else None,
        "geocode_quality": getattr(notice, "geocode_quality", ""),
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
    source_meta = getattr(notice, "source_meta", {}) or {}
    if isinstance(source_meta, dict) and source_meta.get("fixture_id"):
        return "fixture"
    if notice.provider == "LH" and notice.source_id and not str(notice.source_id).isdigit():
        return "LH API"
    if notice.source_id:
        return "DB"
    return "DB"


def _is_fixture_notice(notice: dict[str, Any] | Any) -> bool:
    getter = notice.get if isinstance(notice, dict) else lambda key, default=None: getattr(notice, key, default)
    data_source = str(getter("data_source", "") or "").casefold()
    source_meta = getter("source_meta", {}) or {}
    return "fixture" in data_source or (isinstance(source_meta, dict) and bool(source_meta.get("fixture_id")))


def _metropolitan_region(notice: dict[str, Any]) -> str:
    text = " ".join(
        str(notice.get(key) or "")
        for key in ("region", "district", "title")
    )
    normalized = text.replace(" ", "")
    checks = (
        ("서울", ("서울",)),
        ("부산", ("부산",)),
        ("대구", ("대구",)),
        ("인천", ("인천",)),
        ("광주", ("광주",)),
        ("대전", ("대전",)),
        ("울산", ("울산",)),
        ("세종", ("세종",)),
        ("경기", ("경기", "경기도")),
        ("강원", ("강원",)),
        ("충북", ("충북", "충청북도")),
        ("충남", ("충남", "충청남도")),
        ("전북", ("전북", "전라북도", "전북특별자치도")),
        ("전남", ("전남", "전라남도")),
        ("경북", ("경북", "경상북도")),
        ("경남", ("경남", "경상남도")),
        ("제주", ("제주",)),
    )
    for region, aliases in checks:
        if any(alias.replace(" ", "") in normalized for alias in aliases):
            return region
    return str(notice.get("region") or "")


def _parse_iso_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


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
