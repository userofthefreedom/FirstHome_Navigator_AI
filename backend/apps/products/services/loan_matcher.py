from __future__ import annotations

from datetime import date
from typing import Any

from apps.fixture_store import loan_products
from apps.rules.funding import available_cash, effective_monthly_capacity


PURCHASE_LOAN_PURPOSES = {"purchase", "public_purchase", "first_home_purchase"}
EXCLUDED_LOAN_PURPOSES = {"rent", "jeonse", "monthly_rent", "subscription_collateral", "credit"}
EXCLUDED_LOAN_KEYWORDS = (
    "전세",
    "월세",
    "임차",
    "임대",
    "보증금대출",
    "청약통장담보",
    "청약저축담보",
    "예금담보",
    "신용대출",
    "마이너스통장",
)
FIXTURE_LOAN_SCORE_PENALTY = 8


def match_purchase_loans(
    profile: dict[str, Any],
    funding_plan: dict[str, Any] | None = None,
    *,
    limit: int = 5,
    candidates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for product in candidates if candidates is not None else loan_products():
        if not is_purchase_loan_candidate(product):
            continue
        score, reasons, warnings = purchase_loan_match_score(product, profile, funding_plan or {})
        if _is_fixture_loan(product):
            score = max(0, score - FIXTURE_LOAN_SCORE_PENALTY)
        if score <= 0:
            continue
        next_product = product.copy()
        next_product["match_score"] = score
        next_product["reasons"] = reasons
        next_product["warnings"] = warnings
        ranked.append((score, _loan_source_priority(next_product), next_product))

    return _dedupe_ranked_loan_products(
        sorted(ranked, key=lambda item: (item[1], item[0]), reverse=True),
        limit=limit,
    )


def is_purchase_loan_candidate(product: dict[str, Any]) -> bool:
    purpose = str(product.get("loan_purpose") or "").strip()
    searchable_text = " ".join(
        str(product.get(field) or "")
        for field in ("name", "provider", "category", "description", "target")
    )
    if purpose in EXCLUDED_LOAN_PURPOSES:
        return False
    if any(keyword in searchable_text for keyword in EXCLUDED_LOAN_KEYWORDS):
        return False
    return purpose in PURCHASE_LOAN_PURPOSES


def purchase_loan_match_score(
    product: dict[str, Any],
    profile: dict[str, Any],
    funding_plan: dict[str, Any],
) -> tuple[int, list[str], list[str]]:
    age = date.today().year - int(profile.get("birth_year", date.today().year))
    income = int(profile.get("annual_income", 0) or 0)
    is_homeless = bool(profile.get("is_homeless"))
    price = int(funding_plan.get("price") or 0)
    area_m2 = float(funding_plan.get("exclusive_area_m2") or 0)
    cash_gap = _purchase_cash_gap(profile, funding_plan)
    monthly_capacity = effective_monthly_capacity(profile)

    score = 30
    reasons = ["소유형 청약의 주택 구입 목적 대출 후보입니다."]
    warnings = ["대출 가능 여부와 한도는 금융기관·공공기관 심사 결과에 따라 달라집니다."]

    if int(product.get("age_min", 0) or 0) <= age <= int(product.get("age_max", 150) or 150):
        score += 8
        reasons.append("연령 조건 범위에 들어옵니다.")
    else:
        score -= 8
        warnings.append("연령 조건은 공식 안내에서 다시 확인해야 합니다.")

    max_income = int(product.get("max_income", 0) or 0)
    if max_income <= 0 or income <= max_income:
        score += 12
        reasons.append("입력 소득 기준으로 검토 가능한 후보입니다.")
    else:
        score -= 18
        warnings.append("입력 소득이 후보 상품의 소득 기준을 넘을 수 있습니다.")

    if not product.get("requires_homeless") or is_homeless:
        score += 12
        reasons.append("무주택 또는 생애최초 조건과 방향이 맞습니다.")
    else:
        score -= 20
        warnings.append("무주택 요건이 필요한 상품입니다.")

    max_price = int(product.get("max_price", 0) or 0)
    if price and max_price:
        if price <= max_price:
            score += 8
            reasons.append("선택 주택형 분양가가 상품 가격 기준 안에 있습니다.")
        else:
            score -= 12
            warnings.append("선택 주택형 분양가가 상품 가격 기준을 넘을 수 있습니다.")

    max_area_m2 = float(product.get("max_area_m2") or 0)
    if area_m2 and max_area_m2:
        if area_m2 <= max_area_m2:
            score += 6
            reasons.append("전용면적 기준을 충족할 가능성이 있습니다.")
        else:
            score -= 10
            warnings.append("전용면적 기준을 초과할 수 있습니다.")

    limit_amount = int(product.get("limit_amount", 0) or 0)
    if cash_gap and limit_amount:
        if limit_amount >= cash_gap:
            score += 10
            reasons.append("입주 전 필요 금액 부족분을 한도상 검토할 수 있습니다.")
        elif limit_amount >= cash_gap * 0.7:
            score += 5
            warnings.append("한도가 부족분 전체를 덮지 못할 수 있습니다.")
        else:
            score -= 10
            warnings.append("한도가 현재 부족분 대비 작을 수 있습니다.")

    estimated_monthly_payment = _estimated_monthly_payment(product)
    if estimated_monthly_payment:
        if monthly_capacity and estimated_monthly_payment <= monthly_capacity:
            score += 5
            reasons.append("월 상환 추정액이 입력한 월 납부 감당액 안에 들어올 수 있습니다.")
        elif monthly_capacity:
            score -= 8
            warnings.append("월 상환 추정액이 입력한 월 납부 감당액보다 클 수 있습니다.")

    if product.get("source_url"):
        score += 3

    return max(0, min(score, 100)), reasons[:5], warnings[:4]


def _purchase_cash_gap(profile: dict[str, Any], funding_plan: dict[str, Any]) -> int:
    due_before_move_in = int((funding_plan.get("timeline_summary") or {}).get("due_before_move_in") or 0)
    down_payment_shortfall = int(funding_plan.get("shortfall") or 0)
    current_cash = int(profile.get("asset", 0) or funding_plan.get("available_cash") or available_cash(profile))
    return max(down_payment_shortfall, due_before_move_in - current_cash, 0)


def _estimated_monthly_payment(product: dict[str, Any]) -> int:
    limit_amount = int(product.get("limit_amount", 0) or 0)
    term_years = int(product.get("term_years", 0) or 0)
    if not limit_amount or not term_years:
        return 0
    return max(1, round(limit_amount / (term_years * 12)))


def _loan_source_priority(product: dict[str, Any]) -> int:
    data_source = str(product.get("data_source", "")).casefold()
    if "fixture" in data_source:
        return 0
    if product.get("source_url"):
        return 2
    return 1


def _is_fixture_loan(product: dict[str, Any]) -> bool:
    return "fixture" in str(product.get("data_source", "")).casefold()


def _dedupe_ranked_loan_products(
    ranked: list[tuple[int, int, dict[str, Any]]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_product_keys: set[tuple[str, str, str]] = set()
    skipped: list[dict[str, Any]] = []

    for _score, _source_priority, product in ranked:
        key = _loan_product_key(product)
        if key in seen_product_keys:
            skipped.append(product)
            continue
        selected.append(product)
        seen_product_keys.add(key)
        if len(selected) >= limit:
            return selected

    for product in skipped:
        selected.append(product)
        if len(selected) >= limit:
            break
    return selected


def _loan_product_key(product: dict[str, Any]) -> tuple[str, str, str]:
    provider = str(product.get("provider") or "").strip().casefold()
    category = str(product.get("category") or "").strip().casefold()
    base_name = str(product.get("name") or "").split("(", 1)[0].strip().casefold()
    return provider, category, base_name
