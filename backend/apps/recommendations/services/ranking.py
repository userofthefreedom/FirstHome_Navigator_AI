from __future__ import annotations

import re
from typing import Any

from django.db import OperationalError, ProgrammingError

from apps.fixture_store import current_notices, default_profile
from apps.recommendations.services.scoring import score_detail, score_max, score_reasons
from apps.rules.scoring import option_fit_reasons, option_fit_score, option_funding_insights, option_type_priority


_NOTICE_VERSION_MARKERS = ("정정공고", "정정", "재게시", "재공고", "변경공고")
_BRACKETED_VERSION_MARKER_RE = re.compile(r"[\[(]\s*(?:정정공고|정정|재게시|재공고|변경공고)\s*[\])]")
_PLAIN_PREFIX_VERSION_MARKER_RE = re.compile(r"^\s*(?:정정공고|정정|재게시|재공고|변경공고)\s*[:\-\]]?\s*")
_LEADING_BRACKET_PREFIX_RE = re.compile(r"^\s*(?:\[[^\]]+\]\s*)+")
_TRAILING_QUALIFIER_RE = re.compile(
    r"\s*[\(（](?:기존임차인|상시|유주택|무주택|선착순|순번추첨|동.?호지정|지역제한없음|자격완화|'?\d{2}\.\d{2}\.\d{2}).*?[\)）]\s*$"
)
_VERSION_MARKER_RE = re.compile("|".join(_NOTICE_VERSION_MARKERS))
_REGION_ONLY_RE = re.compile(r"^[가-힣]+(?:특별시|광역시|특별자치도|도|시)(?:\s*외)?$")
_GENERIC_SITE_VALUES = {"전국", "경기 남부", "경기 북부", "공식 공고 확인"}
_FIXTURE_SCORE_PENALTY = {
    "eligibility": 10,
    "funding": 12,
    "schedule": 8,
}
_REGION_ALIAS_KEYS = {
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
    "전남": ("전남", "전라남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
    "강원": ("강원", "강원특별자치도"),
    "세종": ("세종", "세종특별자치시"),
}
_WHITESPACE_RE = re.compile(r"\s+")


def _area_m2(value: str) -> float:
    digits = "".join(char if char.isdigit() or char == "." else " " for char in str(value or ""))
    for token in digits.split():
        try:
            return float(token)
        except ValueError:
            continue
    return 0


def _option_fit_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    price = int(notice.get("price") or 0)
    return option_fit_score(
        {
            "exclusive_area_m2": _area_m2(notice.get("area", "")),
            "base_price": price,
            "down_payment": round(price * float(notice.get("contract_rate", 0.1))) if price else 0,
            "middle_payment": round(price * float(notice.get("middle_payment_rate", 0.6))) if price else 0,
        },
        profile,
    )


def _notice_group_key(notice: dict[str, Any]) -> tuple[str, ...]:
    provider = _normalize_key_text(notice.get("provider", ""))
    site = _notice_site_value(notice)
    if site:
        return ("site", provider, _normalize_key_text(site), _notice_family_key(notice))
    return (
        "title",
        provider,
        _normalize_key_text(notice.get("region", "")),
        _normalize_key_text(_base_notice_title(notice.get("title", ""))),
    )


def _base_notice_title(title: Any) -> str:
    text = str(title or "")
    previous = None
    while previous != text:
        previous = text
        text = _BRACKETED_VERSION_MARKER_RE.sub(" ", text)
        text = _PLAIN_PREFIX_VERSION_MARKER_RE.sub("", text)
        text = _LEADING_BRACKET_PREFIX_RE.sub("", text)
        text = _TRAILING_QUALIFIER_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalize_key_text(value: Any) -> str:
    return _WHITESPACE_RE.sub("", str(value or "")).casefold()


def _filter_by_preferred_regions(notices: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    preferred_regions = [
        str(region or "").strip()
        for region in profile.get("preferred_regions", [])
        if str(region or "").strip()
    ]
    if not preferred_regions:
        return notices
    return [
        notice
        for notice in notices
        if any(_notice_matches_preferred_region(notice, region) for region in preferred_regions)
    ]


def _notice_matches_preferred_region(notice: dict[str, Any], preferred_region: str) -> bool:
    preferred_key = _normalize_key_text(preferred_region)
    region_key = _normalize_key_text(notice.get("region", ""))
    text_key = _normalize_key_text(
        " ".join(
            [
                str(notice.get("region") or ""),
                str(notice.get("district") or ""),
                str(notice.get("title") or ""),
                _notice_site_value(notice),
            ]
        )
    )

    if preferred_key in {"경기", "경기도"}:
        return "경기" in text_key
    if preferred_key == "경기북부":
        return "경기북부" in text_key or region_key in {"경기북부", "경기"}
    if preferred_key == "경기남부":
        return "경기북부" not in text_key and (region_key in {"경기남부", "경기"} or "경기남부" in text_key)
    return any(_normalize_key_text(alias) in text_key for alias in _REGION_ALIAS_KEYS.get(preferred_key, (preferred_key,)))


def _notice_site_value(notice: dict[str, Any]) -> str:
    source_meta = notice.get("source_meta")
    supply_summary = source_meta.get("supply_summary") if isinstance(source_meta, dict) else None
    candidates = []
    if isinstance(supply_summary, dict):
        candidates.append(supply_summary.get("district"))
    candidates.append(notice.get("district"))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if _is_specific_site(text):
            return text
    return ""


def _is_specific_site(value: str) -> bool:
    if not value or value in _GENERIC_SITE_VALUES:
        return False
    return _REGION_ONLY_RE.match(value) is None


def _notice_family_key(notice: dict[str, Any]) -> str:
    return _normalize_key_text(
        " ".join(
            str(notice.get(key) or "")
            for key in ("ownership_type", "supply_type")
        )
    )


def _latest_notice_versions(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, ...], dict[str, Any]] = {}
    for notice in notices:
        key = _notice_group_key(notice)
        current = selected.get(key)
        if current is None or _notice_version_key(notice) > _notice_version_key(current):
            selected[key] = notice
    return list(selected.values())


def _notice_version_key(notice: dict[str, Any]) -> tuple[int, int, int]:
    return (
        _version_marker_count(notice.get("title", "")),
        _numeric_source_value(_notice_source_version(notice)),
        int(notice.get("id") or 0),
    )


def _version_marker_count(title: Any) -> int:
    text = str(title or "")
    return len(_VERSION_MARKER_RE.findall(text))


def _notice_source_version(notice: dict[str, Any]) -> Any:
    source_meta = notice.get("source_meta")
    if isinstance(source_meta, dict):
        return source_meta.get("pan_id") or notice.get("source_id")
    return notice.get("source_id")


def _numeric_source_value(value: Any) -> int:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return int(digits) if digits else 0


def _ranked_unit_options(notice_id: int, profile: dict[str, Any], *, limit: int = 3) -> list[dict[str, Any]]:
    try:
        from apps.notice_docs.models import HousingUnitOption

        options = (
            HousingUnitOption.objects.filter(notice_id=notice_id)
            .prefetch_related("payment_schedules")
            .order_by("-confidence", "exclusive_area_m2", "id")
        )
        serialized = [_serialize_unit_option(option) for option in options]
    except (OperationalError, ProgrammingError):
        return []

    if not serialized:
        return []
    for option in serialized:
        option["option_fit_score"] = option_fit_score(option, profile)
        option["fit_reasons"] = option_fit_reasons(option, profile)
        option["funding_insights"] = option_funding_insights(option, profile)
        option["selection_factors"] = _option_selection_factors(option)
    return sorted(
        serialized,
        key=lambda item: (option_type_priority(item["option_type"]), item["option_fit_score"], item["confidence"]),
        reverse=True,
    )[:limit]


def _serialize_unit_option(option: Any) -> dict[str, Any]:
    schedules = list(option.payment_schedules.all())
    down_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "down_payment")
    middle_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "middle_payment")
    installment_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "installment_payment")
    final_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "final_payment")
    extraction = getattr(option, "extraction", None)
    extraction_source = (
        extraction.raw_json.get("source", "")
        if extraction and isinstance(getattr(extraction, "raw_json", None), dict)
        else _option_fallback_source(option)
    )
    return {
        "option_id": option.id,
        "unit_type": option.unit_type,
        "exclusive_area_m2": option.exclusive_area_m2,
        "floor_group": option.floor_group,
        "option_type": option.option_type,
        "base_price": option.base_price,
        "loan_amount": option.loan_amount,
        "balcony_extension_price": option.balcony_extension_price,
        "confidence": option.confidence,
        "source_page": option.source_page,
        "extraction_source": extraction_source,
        "down_payment": down_payment,
        "middle_payment": middle_payment,
        "installment_payment": installment_payment,
        "final_payment": final_payment,
        "payment_schedules": [
            {
                "label": schedule.label,
                "due_date": schedule.due_date.isoformat() if schedule.due_date else "",
                "amount": schedule.amount,
                "payment_type": schedule.payment_type,
                "sequence": schedule.sequence,
            }
            for schedule in schedules
        ],
    }


def _option_fallback_source(option: Any) -> str:
    if str(getattr(option, "source_text", "") or "").startswith("LH 공급정보 API"):
        return "lh_supply_info"
    return ""


def calculate_score(notice: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or default_profile()
    detail = _score_detail_with_source_penalty(notice, score_detail(notice, profile))
    top_options = _ranked_unit_options(int(notice["id"]), profile, limit=3)
    best_option = top_options[0] if top_options else None
    option_fit_score = best_option["option_fit_score"] if best_option else _option_fit_score(notice, profile)
    total_score = sum(detail.values())
    explanations = _recommendation_explanations(notice, detail, best_option)
    return {
        "notice_id": notice["id"],
        "source_id": notice.get("source_id", ""),
        "data_source": notice.get("data_source", "fixture"),
        "is_price_confirmed": notice.get("is_price_confirmed", int(notice.get("price") or 0) > 0),
        "source_meta": notice.get("source_meta", {}),
        "ownership_type": notice.get("ownership_type", "unknown"),
        "is_service_target": notice.get("is_service_target", False),
        "exclude_reason": notice.get("exclude_reason", ""),
        "official_document_status": notice.get("official_document_status", "not_requested"),
        "analysis_summary": notice.get("analysis_summary", {}),
        "document_count": notice.get("document_count", 0),
        "unit_option_count": notice.get("unit_option_count", 0),
        "title": notice["title"],
        "provider": notice["provider"],
        "region": notice["region"],
        "district": notice["district"],
        "supply_type": notice["supply_type"],
        "housing_type": notice["housing_type"],
        "area": notice["area"],
        "price": notice["price"],
        "application_deadline": notice["application_deadline"],
        "winner_date": notice["winner_date"],
        "contract_date": notice["contract_date"],
        "move_in": notice["move_in"],
        "competition": notice["competition"],
        "source_url": notice.get("source_url", ""),
        "total_score": total_score,
        "score_max": score_max(),
        "option_fit_score": option_fit_score,
        "best_option": best_option,
        "top_options": top_options,
        "score_detail": detail,
        "reasons": score_reasons(notice, profile),
        "explanations": explanations,
        "selection_summary": explanations[0]["message"] if explanations else "",
    }


def recommendation_candidate_notices(profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    profile = profile or default_profile()
    return _filter_by_preferred_regions(_latest_notice_versions(current_notices()), profile)


def ranked_recommendations(profile: dict[str, Any] | None = None, limit: int = 3) -> list[dict[str, Any]]:
    profile = profile or default_profile()
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in recommendation_candidate_notices(profile)],
        key=lambda item: (item["total_score"], item["option_fit_score"]),
        reverse=True,
    )
    return recommendations[:limit]


def _option_selection_factors(option: dict[str, Any]) -> list[dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    insights = option.get("funding_insights") or {}
    option_type = option.get("option_type", "")
    if option_type == "general_supply":
        factors.append({"code": "default_group", "label": "본청약 기준", "message": "일반적인 본청약 납부안을 우선 기준으로 봅니다."})
    elif option_type == "pre_subscription":
        factors.append({"code": "pre_subscription_group", "label": "사전청약 그룹", "message": "사전청약 당첨자 납부안으로 별도 비교합니다."})
    elif option_type == "minus":
        factors.append({"code": "minus_option", "label": "마이너스 옵션", "message": "마이너스 옵션 금액이 반영된 대안입니다."})
    if int(option.get("loan_amount") or 0) > 0:
        factors.append({"code": "loan_amount", "label": "융자금 포함", "message": "분양가에 포함된 융자금을 잔금 이후 상환 항목으로 분리했습니다."})
    if option.get("payment_schedules"):
        factors.append({"code": "payment_schedule", "label": "공식 일정", "message": "공고문 납부 일정에서 계약금과 중도금 흐름을 계산했습니다."})
    if insights:
        if int(insights.get("down_payment_shortfall") or 0) > 0:
            factors.append(
                {
                    "code": "down_payment_shortfall",
                    "label": "계약금 부족액",
                    "message": f"{int(insights.get('down_payment_shortfall') or 0):,}원을 월 {int(insights.get('down_payment_monthly_target') or 0):,}원씩 준비해야 합니다.",
                }
            )
        elif int(insights.get("down_payment") or 0) > 0:
            factors.append({"code": "down_payment_ready", "label": "계약금", "message": "현재 현금 기준 계약금 부담이 낮은 편입니다."})
        if int(insights.get("monthly_schedule_need") or 0) > 0:
            factors.append(
                {
                    "code": "monthly_schedule_need",
                    "label": "월 준비 목표",
                    "message": f"중도금·할부금 흐름은 월 약 {int(insights.get('monthly_schedule_need') or 0):,}원 기준으로 봅니다.",
                }
            )
    return factors


def _recommendation_explanations(
    notice: dict[str, Any],
    detail: dict[str, int],
    best_option: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    explanations = []
    if best_option:
        option_label = " · ".join(
            part
            for part in [str(best_option.get("unit_type") or ""), str(best_option.get("floor_group") or "")]
            if part
        )
        explanations.append(
            {
                "code": "best_option",
                "label": "대표 주택형",
                "message": f"{option_label} 옵션을 기본 비교 대상으로 선택했습니다.",
                "option_id": best_option.get("option_id"),
            }
        )
    elif int(notice.get("price") or 0) > 0:
        explanations.append({"code": "representative_price", "label": "대표 분양가", "message": "주택형 상세 추출 전이라 공고 목록의 대표 분양가로 계산했습니다."})
    return explanations


def _score_detail_with_source_penalty(notice: dict[str, Any], detail: dict[str, int]) -> dict[str, int]:
    if not _is_fixture_notice(notice):
        return detail
    adjusted = detail.copy()
    for key, penalty in _FIXTURE_SCORE_PENALTY.items():
        adjusted[key] = max(0, adjusted.get(key, 0) - penalty)
    return adjusted


def _is_fixture_notice(notice: dict[str, Any]) -> bool:
    source = str(notice.get("data_source") or "").casefold()
    source_meta = notice.get("source_meta") or {}
    return "fixture" in source or (isinstance(source_meta, dict) and bool(source_meta.get("fixture_id")))
