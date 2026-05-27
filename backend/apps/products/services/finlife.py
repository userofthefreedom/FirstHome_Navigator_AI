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


def _monthly_limit(value: Any, category: str) -> int:
    if category != "적금":
        return 0
    return max(_to_int(value), 0)
