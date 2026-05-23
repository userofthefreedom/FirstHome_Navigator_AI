from __future__ import annotations

from typing import Any

from django.db import OperationalError, ProgrammingError

from apps.fixture_store import default_profile, notices
from apps.recommendations.services.scoring import score_detail, score_reasons


def _area_m2(value: str) -> float:
    digits = "".join(char if char.isdigit() or char == "." else " " for char in str(value or ""))
    for token in digits.split():
        try:
            return float(token)
        except ValueError:
            continue
    return 0


def _option_fit_score(notice: dict[str, Any], profile: dict[str, Any]) -> int:
    score = 0
    area = _area_m2(notice.get("area", ""))
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(notice.get("price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        score += 35
    elif not area or (min_area and area >= min_area * 0.9) or (max_area and area <= max_area * 1.1):
        score += 15

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        score += 35
    elif not price:
        score += 10
    elif (min_price and price >= min_price * 0.9) or (max_price and price <= max_price * 1.1):
        score += 15

    down_payment = round(price * float(notice.get("contract_rate", 0.1))) if price else 0
    if down_payment and max_down_payment and down_payment <= max_down_payment:
        score += 20
    elif down_payment:
        score += 8
    else:
        score += 5

    middle_payment = round(price * float(notice.get("middle_payment_rate", 0.6))) if price else 0
    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        score += 10
    elif monthly_need:
        score += 4
    else:
        score += 5

    return min(score, 100)


def _unit_option_fit_score(option: dict[str, Any], profile: dict[str, Any]) -> int:
    score = 0
    area = float(option.get("exclusive_area_m2") or 0)
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(option.get("base_price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)
    down_payment = int(option.get("down_payment") or 0)
    middle_payment = int(option.get("middle_payment") or 0)

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        score += 35
    elif area and ((min_area and area >= min_area * 0.9) or (max_area and area <= max_area * 1.1)):
        score += 15

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        score += 35
    elif price and ((min_price and price >= min_price * 0.9) or (max_price and price <= max_price * 1.1)):
        score += 15
    elif not price:
        score += 10

    if down_payment and max_down_payment and down_payment <= max_down_payment:
        score += 20
    elif down_payment:
        score += 8
    else:
        score += 5

    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        score += 10
    elif monthly_need:
        score += 4
    else:
        score += 5

    return min(score, 100)


def _unit_option_fit_reasons(option: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    area = float(option.get("exclusive_area_m2") or 0)
    min_area = float(profile.get("desired_area_min_m2") or 0)
    max_area = float(profile.get("desired_area_max_m2") or 0)
    price = int(option.get("base_price") or 0)
    min_price = int(profile.get("desired_price_min") or 0)
    max_price = int(profile.get("desired_price_max") or 0)
    down_payment = int(option.get("down_payment") or 0)
    middle_payment = int(option.get("middle_payment") or 0)
    max_down_payment = int(profile.get("max_down_payment") or 0)
    monthly_capacity = int(profile.get("monthly_payment_capacity") or profile.get("monthly_saving") or 0)

    if area and (not min_area or area >= min_area) and (not max_area or area <= max_area):
        reasons.append("희망 면적 범위에 들어옵니다.")
    elif area:
        reasons.append("희망 면적과 가까운 대안입니다.")

    if price and (not min_price or price >= min_price) and (not max_price or price <= max_price):
        reasons.append("희망 분양가 범위에 들어옵니다.")
    elif price:
        reasons.append("희망 분양가와 차이가 있어 자금 여유를 확인해야 합니다.")
    else:
        reasons.append("분양가 근거가 부족해 공식 공고문 확인이 필요합니다.")

    if down_payment and max_down_payment and down_payment <= max_down_payment:
        reasons.append("계약금이 설정한 준비 가능 금액 안에 있습니다.")
    elif down_payment:
        reasons.append("계약금 준비액이 부족할 수 있습니다.")

    monthly_need = middle_payment // 24 if middle_payment else 0
    if monthly_need and monthly_capacity and monthly_need <= monthly_capacity:
        reasons.append("중도금 예상 부담이 월 저축 여력 안에 있습니다.")
    elif monthly_need:
        reasons.append("중도금 납부 계획은 추가 자금 점검이 필요합니다.")

    return reasons[:4]


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
        option["option_fit_score"] = _unit_option_fit_score(option, profile)
        option["fit_reasons"] = _unit_option_fit_reasons(option, profile)
    return sorted(serialized, key=lambda item: (item["option_fit_score"], item["confidence"]), reverse=True)[:limit]


def _serialize_unit_option(option: Any) -> dict[str, Any]:
    schedules = list(option.payment_schedules.all())
    down_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "down_payment")
    middle_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "middle_payment")
    final_payment = sum(schedule.amount for schedule in schedules if schedule.payment_type == "final_payment")
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
        "down_payment": down_payment,
        "middle_payment": middle_payment,
        "final_payment": final_payment,
    }


def calculate_score(notice: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or default_profile()
    detail = score_detail(notice, profile)
    top_options = _ranked_unit_options(int(notice["id"]), profile, limit=3)
    best_option = top_options[0] if top_options else None
    option_fit_score = best_option["option_fit_score"] if best_option else _option_fit_score(notice, profile)
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
        "total_score": sum(detail.values()),
        "option_fit_score": option_fit_score,
        "best_option": best_option,
        "top_options": top_options,
        "score_detail": detail,
        "reasons": score_reasons(notice, profile),
    }


def ranked_recommendations(profile: dict[str, Any] | None = None, limit: int = 3) -> list[dict[str, Any]]:
    profile = profile or default_profile()
    recommendations = sorted(
        [calculate_score(notice, profile) for notice in notices()],
        key=lambda item: (item["option_fit_score"], item["total_score"]),
        reverse=True,
    )
    return recommendations[:limit]
