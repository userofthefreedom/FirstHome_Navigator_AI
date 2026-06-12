from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import requests


FINLIFE_BASE_URL = "https://finlife.fss.or.kr/finlifeapi"
FINLIFE_SOURCE_URL = "https://finlife.fss.or.kr/finlife/main/contents.do?menuNo=700029"
PRODUCT_ENDPOINTS = {
    "deposit": ("depositProductsSearch.json", "예금"),
    "saving": ("savingProductsSearch.json", "적금"),
}
LOAN_ENDPOINTS = {
    "mortgage": ("mortgageLoanProductsSearch.json", "주택담보대출"),
}


@dataclass(frozen=True)
class FinlifeProduct:
    name: str
    provider: str
    category: str
    rate: str
    monthly_limit: int
    term_months: int
    protection_status: bool
    source_url: str
    reasons: list[str]


@dataclass(frozen=True)
class FinlifeLoanProduct:
    name: str
    provider: str
    category: str
    loan_purpose: str
    description: str
    target: str
    rate: str
    limit: str
    limit_amount: int
    term: str
    term_years: int
    age_min: int
    age_max: int
    max_income: int
    max_price: int
    max_area_m2: float
    requires_homeless: bool
    source_url: str
    reasons: list[str]
    caveats: list[str]


def fetch_finlife_payload(
    api_key: str,
    kind: str,
    *,
    top_fin_grp_no: str = "020000",
    page_no: int = 1,
    timeout: int = 30,
) -> dict[str, Any]:
    endpoint, _category = PRODUCT_ENDPOINTS[kind]
    response = requests.get(
        f"{FINLIFE_BASE_URL}/{endpoint}",
        params={"auth": api_key, "topFinGrpNo": top_fin_grp_no, "pageNo": str(page_no)},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", {})
    if result.get("err_cd") != "000":
        raise ValueError(f"Finlife API error {result.get('err_cd')}: {result.get('err_msg')}")
    return payload


def fetch_finlife_loan_payload(
    api_key: str,
    kind: str,
    *,
    top_fin_grp_no: str = "020000",
    page_no: int = 1,
    timeout: int = 30,
) -> dict[str, Any]:
    endpoint, _category = LOAN_ENDPOINTS[kind]
    response = requests.get(
        f"{FINLIFE_BASE_URL}/{endpoint}",
        params={"auth": api_key, "topFinGrpNo": top_fin_grp_no, "pageNo": str(page_no)},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", {})
    if result.get("err_cd") != "000":
        raise ValueError(f"Finlife API error {result.get('err_cd')}: {result.get('err_msg')}")
    return payload


def fetch_all_finlife_products(
    api_key: str,
    *,
    kinds: list[str],
    top_fin_grp_no: str = "020000",
    timeout: int = 30,
) -> list[FinlifeProduct]:
    products: list[FinlifeProduct] = []
    for kind in kinds:
        page_no = 1
        while True:
            payload = fetch_finlife_payload(
                api_key,
                kind,
                top_fin_grp_no=top_fin_grp_no,
                page_no=page_no,
                timeout=timeout,
            )
            result = payload.get("result", {})
            products.extend(normalize_finlife_products(result, kind))

            max_page_no = int(result.get("max_page_no") or page_no)
            if page_no >= max_page_no:
                break
            page_no += 1
    return products


def fetch_all_finlife_loans(
    api_key: str,
    *,
    kinds: list[str],
    top_fin_grp_no: str = "020000",
    timeout: int = 30,
) -> list[FinlifeLoanProduct]:
    products: list[FinlifeLoanProduct] = []
    for kind in kinds:
        page_no = 1
        while True:
            payload = fetch_finlife_loan_payload(
                api_key,
                kind,
                top_fin_grp_no=top_fin_grp_no,
                page_no=page_no,
                timeout=timeout,
            )
            result = payload.get("result", {})
            products.extend(normalize_finlife_loan_products(result, kind))

            max_page_no = int(result.get("max_page_no") or page_no)
            if page_no >= max_page_no:
                break
            page_no += 1
    return products


def normalize_finlife_products(result: dict[str, Any], kind: str) -> list[FinlifeProduct]:
    _endpoint, category = PRODUCT_ENDPOINTS[kind]
    base_by_code = {item.get("fin_prdt_cd"): item for item in result.get("baseList") or []}
    options_by_code: dict[str, list[dict[str, Any]]] = {}
    for option in result.get("optionList") or []:
        options_by_code.setdefault(option.get("fin_prdt_cd"), []).append(option)

    normalized: list[FinlifeProduct] = []
    for code, base in base_by_code.items():
        options = options_by_code.get(code) or [{}]
        for option in options:
            term_months = _to_int(option.get("save_trm"))
            max_rate = _max_decimal(option.get("intr_rate"), option.get("intr_rate2"))
            provider = str(base.get("kor_co_nm") or "").strip()
            product_name = str(base.get("fin_prdt_nm") or "").strip()
            if not provider or not product_name:
                continue

            display_name = f"{product_name} ({term_months}개월)" if term_months else product_name
            join_way = str(base.get("join_way") or "공식 상품 설명 확인").strip()
            rate_label = f"최고 연 {max_rate:.2f}%" if max_rate is not None else "공시 금리 확인 필요"
            monthly_limit = _monthly_limit(base.get("max_limit"), category)

            normalized.append(
                FinlifeProduct(
                    name=display_name[:120],
                    provider=provider[:60],
                    category=category,
                    rate=rate_label,
                    monthly_limit=monthly_limit,
                    term_months=term_months,
                    protection_status=True,
                    source_url=FINLIFE_SOURCE_URL,
                    reasons=[
                        f"금융감독원 금융상품통합비교공시에서 수집한 {category} 상품입니다.",
                        f"가입 방법: {join_way}",
                    ],
                )
            )
    return normalized


def normalize_finlife_loan_products(result: dict[str, Any], kind: str) -> list[FinlifeLoanProduct]:
    _endpoint, category = LOAN_ENDPOINTS[kind]
    base_by_code = {item.get("fin_prdt_cd"): item for item in result.get("baseList") or []}
    options_by_code: dict[str, list[dict[str, Any]]] = {}
    for option in result.get("optionList") or []:
        options_by_code.setdefault(option.get("fin_prdt_cd"), []).append(option)

    normalized: list[FinlifeLoanProduct] = []
    for code, base in base_by_code.items():
        provider = str(base.get("kor_co_nm") or "").strip()
        product_name = str(base.get("fin_prdt_nm") or "").strip()
        if not provider or not product_name:
            continue

        options = options_by_code.get(code) or [{}]
        loan_limit = str(base.get("loan_lmt") or "공식 상품 설명 확인").strip()
        join_way = str(base.get("join_way") or "공식 상품 설명 확인").strip()
        early_fee = str(base.get("erly_rpay_fee") or "").strip()
        extra_cost = str(base.get("loan_inci_expn") or "").strip()
        delay_rate = str(base.get("dly_rate") or "").strip()

        for option in options:
            mortgage_type = str(option.get("mrtg_type_nm") or "").strip()
            repay_type = str(option.get("rpay_type_nm") or "").strip()
            rate_type = str(option.get("lend_rate_type_nm") or "").strip()
            min_rate = _max_decimal(option.get("lend_rate_min"))
            max_rate = _max_decimal(option.get("lend_rate_max"))
            avg_rate = _max_decimal(option.get("lend_rate_avg"))
            rate_label = _loan_rate_label(min_rate, max_rate, avg_rate)
            display_bits = [bit for bit in (mortgage_type, repay_type, rate_type) if bit]
            display_name = product_name if not display_bits else f"{product_name} ({' · '.join(display_bits)})"

            normalized.append(
                FinlifeLoanProduct(
                    name=display_name[:160],
                    provider=provider[:80],
                    category=category,
                    loan_purpose="purchase",
                    description="금융감독원 금융상품통합비교공시에서 수집한 주택담보대출 상품입니다. 공공분양 잔금 또는 주택 구입자금으로 활용 가능한지는 금융기관 심사가 필요합니다.",
                    target="주택 구입 예정자 및 담보대출 심사 대상자",
                    rate=rate_label,
                    limit=loan_limit[:120],
                    limit_amount=_amount_from_text(loan_limit),
                    term="상품별 공식 약정기간 확인",
                    term_years=30,
                    age_min=19,
                    age_max=70,
                    max_income=0,
                    max_price=0,
                    max_area_m2=0,
                    requires_homeless=False,
                    source_url=FINLIFE_SOURCE_URL,
                    reasons=[
                        f"금융감독원 금융상품통합비교공시의 {category} 상품입니다.",
                        f"상환 방식: {repay_type or '공식 확인'}",
                        f"금리 유형: {rate_type or '공식 확인'}",
                    ],
                    caveats=[
                        "LTV, DSR, 담보평가, 소득, 신용도, 공공분양 대출 규정에 따라 실제 승인 여부가 달라집니다.",
                        f"가입 방법: {join_way}",
                        *( [f"중도상환수수료: {early_fee}"] if early_fee else [] ),
                        *( [f"대출 부대비용: {extra_cost}"] if extra_cost else [] ),
                        *( [f"연체 이자율: {delay_rate}"] if delay_rate else [] ),
                    ][:5],
                )
            )
    return normalized


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _max_decimal(*values: Any) -> Decimal | None:
    candidates: list[Decimal] = []
    for value in values:
        if value in (None, ""):
            continue
        try:
            candidates.append(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            continue
    return max(candidates) if candidates else None


def _loan_rate_label(min_rate: Decimal | None, max_rate: Decimal | None, avg_rate: Decimal | None) -> str:
    if min_rate is not None and max_rate is not None:
        return f"최저 연 {min_rate:.2f}% ~ 최고 연 {max_rate:.2f}%"
    if avg_rate is not None:
        return f"평균 연 {avg_rate:.2f}%"
    if min_rate is not None:
        return f"최저 연 {min_rate:.2f}%"
    if max_rate is not None:
        return f"최고 연 {max_rate:.2f}%"
    return "공시 금리 확인 필요"


def _amount_from_text(value: Any) -> int:
    text = str(value or "").replace(",", "").replace(" ", "")
    if not text:
        return 0
    import re

    best = 0
    for match in re.finditer(r"(\d+(?:\.\d+)?)(억|만원|원)", text):
        number = Decimal(match.group(1))
        unit = match.group(2)
        if unit == "억":
            amount = int(number * 100_000_000)
        elif unit == "만원":
            amount = int(number * 10_000)
        else:
            amount = int(number)
        best = max(best, amount)
    return best


def _monthly_limit(value: Any, category: str) -> int:
    if category != "적금":
        return 0
    return max(_to_int(value), 0)
