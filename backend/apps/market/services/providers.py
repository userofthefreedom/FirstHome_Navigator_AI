from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from xml.etree import ElementTree

import requests


DATA_GO_GOLD_URL = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
MOLIT_APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
KOREAEXIM_EXCHANGE_URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
METALS_DEV_BASE_URL = "https://api.metals.dev/v1"
ECOS_STATISTIC_SEARCH_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
KRX_BASE_URL = "https://data-dbg.krx.co.kr/svc/apis"

SOURCE_GOLD = "data.go.kr:fsc-general-product"
SOURCE_SILVER = "metals.dev"
SOURCE_EXCHANGE = "koreaexim"
SOURCE_ECOS = "bok-ecos"
SOURCE_KRX = "krx-openapi"
SOURCE_ESTATE = "data.go.kr:molit-apt-trade"


@dataclass(frozen=True)
class MarketPriceRow:
    asset_type: str
    base_date: date
    price: float
    change_rate: float = 0
    source: str = ""
    source_meta: dict[str, Any] | None = None


class MarketDataError(ValueError):
    pass


def fetch_gold_rows(api_key: str, *, start: date, end: date, timeout: int = 30) -> list[MarketPriceRow]:
    payload = _request_json(
        DATA_GO_GOLD_URL,
        params={
            "serviceKey": api_key,
            "pageNo": "1",
            "numOfRows": "1000",
            "resultType": "json",
            "beginBasDt": _ymd(start),
            "endBasDt": _ymd(end),
        },
        timeout=timeout,
    )
    body = payload.get("response", {}).get("body", {})
    items = _ensure_list(body.get("items", {}).get("item"))
    rows: list[MarketPriceRow] = []
    seen_dates: set[date] = set()
    for item in items:
        if str(item.get("srtnCd") or "") != "04020000":
            continue
        base_date = _parse_yyyymmdd(item.get("basDt"))
        price = _to_float(item.get("clpr"))
        if not base_date or price <= 0 or base_date in seen_dates:
            continue
        seen_dates.add(base_date)
        rows.append(
            MarketPriceRow(
                asset_type="gold",
                base_date=base_date,
                price=price,
                change_rate=_to_float(item.get("fltRt")),
                source=SOURCE_GOLD,
                source_meta={
                    "unit": "KRW/g",
                    "item_name": item.get("itmsNm"),
                    "srtn_cd": item.get("srtnCd"),
                    "market": "KRX gold 99.99 1kg",
                },
            )
        )
    return sorted(rows, key=lambda row: row.base_date)


def fetch_silver_rows(api_key: str, *, start: date, end: date, timeout: int = 30) -> list[MarketPriceRow]:
    rows: list[MarketPriceRow] = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(end, chunk_start + timedelta(days=29))
        payload = _request_json(
            f"{METALS_DEV_BASE_URL}/timeseries",
            params={"api_key": api_key, "start_date": chunk_start.isoformat(), "end_date": chunk_end.isoformat()},
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        if payload.get("status") != "success":
            raise MarketDataError(payload.get("error_message") or "Metals.dev timeseries request failed.")
        rates = payload.get("rates") or {}
        for date_key, entry in rates.items():
            base_date = _parse_iso_date(date_key)
            price = _to_float((entry.get("metals") or {}).get("silver"))
            if base_date and price > 0:
                rows.append(
                    MarketPriceRow(
                        asset_type="silver",
                        base_date=base_date,
                        price=price,
                        source=SOURCE_SILVER,
                        source_meta={"unit": "USD/toz", "endpoint": "timeseries"},
                    )
                )
        chunk_start = chunk_end + timedelta(days=1)

    if not rows:
        rows = [fetch_silver_spot_row(api_key, timeout=timeout)]
    return _with_computed_change(sorted(rows, key=lambda row: row.base_date))


def fetch_silver_spot_row(api_key: str, *, timeout: int = 30) -> MarketPriceRow:
    payload = _request_json(
        f"{METALS_DEV_BASE_URL}/metal/spot",
        params={"api_key": api_key, "metal": "silver", "currency": "USD"},
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    if payload.get("status") != "success":
        raise MarketDataError(payload.get("error_message") or "Metals.dev silver spot request failed.")
    rate = payload.get("rate") or {}
    timestamp = str(payload.get("timestamp") or "")
    base_date = _parse_iso_date(timestamp[:10]) or date.today()
    return MarketPriceRow(
        asset_type="silver",
        base_date=base_date,
        price=_to_float(rate.get("price")),
        change_rate=_to_float(rate.get("change_percent")),
        source=SOURCE_SILVER,
        source_meta={"unit": "USD/toz", "endpoint": "metal/spot"},
    )


def fetch_exchange_rows(api_key: str, *, target_date: date, timeout: int = 30) -> list[MarketPriceRow]:
    for offset in range(0, 14):
        search_date = target_date - timedelta(days=offset)
        payload = _request_json(
            KOREAEXIM_EXCHANGE_URL,
            params={"authkey": api_key, "searchdate": _ymd(search_date), "data": "AP01"},
            timeout=timeout,
        )
        rows = _normalize_exchange_payload(payload, search_date)
        if rows:
            return rows
    return []


def fetch_ecos_base_rate_rows(api_key: str, *, start: date, end: date, timeout: int = 30) -> list[MarketPriceRow]:
    url = (
        f"{ECOS_STATISTIC_SEARCH_URL}/{api_key}/json/kr/1/1000/"
        f"722Y001/D/{_ymd(start)}/{_ymd(end)}/0101000"
    )
    payload = _request_json(url, timeout=timeout)
    result = payload.get("StatisticSearch") or {}
    if "RESULT" in result:
        code = result["RESULT"].get("CODE")
        message = result["RESULT"].get("MESSAGE")
        raise MarketDataError(f"ECOS API error {code}: {message}")
    rows = []
    for item in _ensure_list(result.get("row")):
        base_date = _parse_yyyymmdd(item.get("TIME"))
        value = _to_float(item.get("DATA_VALUE"))
        if base_date and value > 0:
            rows.append(
                MarketPriceRow(
                    asset_type="base_rate",
                    base_date=base_date,
                    price=value,
                    source=SOURCE_ECOS,
                    source_meta={
                        "unit": "%",
                        "stat_code": "722Y001",
                        "item_code": "0101000",
                        "item_name": item.get("ITEM_NAME1"),
                    },
                )
            )
    return _with_computed_change(sorted(rows, key=lambda row: row.base_date))


def fetch_krx_index_rows(api_key: str, *, target_date: date, timeout: int = 30) -> list[MarketPriceRow]:
    rows: list[MarketPriceRow] = []
    rows.extend(_fetch_krx_index_endpoint(api_key, "kospi", "idx/kospi_dd_trd", target_date, timeout=timeout))
    rows.extend(_fetch_krx_index_endpoint(api_key, "kosdaq", "idx/kosdaq_dd_trd", target_date, timeout=timeout))
    return rows


def fetch_estate_trade_rows(api_key: str, *, month: date, lawd_cd: str = "11110", timeout: int = 30) -> list[MarketPriceRow]:
    payload = _request_text(
        MOLIT_APT_TRADE_URL,
        params={
            "serviceKey": api_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": f"{month.year}{month.month:02d}",
            "pageNo": "1",
            "numOfRows": "1000",
        },
        timeout=timeout,
    )
    root = ElementTree.fromstring(payload)
    result_code = root.findtext("./header/resultCode")
    if result_code not in {"000", "00", None}:
        raise MarketDataError(root.findtext("./header/resultMsg") or f"MOLIT API error {result_code}")
    amounts = []
    for item in root.findall(".//item"):
        amount = _to_float(item.findtext("dealAmount"))
        if amount > 0:
            amounts.append(amount)
    if not amounts:
        return []
    average = round(sum(amounts) / len(amounts), 2)
    return [
        MarketPriceRow(
            asset_type="estate_apt_trade_avg",
            base_date=date(month.year, month.month, 1),
            price=average,
            source=SOURCE_ESTATE,
            source_meta={
                "unit": "만원",
                "lawd_cd": lawd_cd,
                "deal_count": len(amounts),
                "label": "서울 종로구 아파트 평균 실거래가",
            },
        )
    ]


def previous_month(anchor: date) -> date:
    first_day = date(anchor.year, anchor.month, 1)
    return first_day - timedelta(days=1)


def _fetch_krx_index_endpoint(
    api_key: str,
    asset_type: str,
    endpoint: str,
    target_date: date,
    *,
    timeout: int,
) -> list[MarketPriceRow]:
    for offset in range(0, 14):
        base_date = target_date - timedelta(days=offset)
        payload = _request_json(
            f"{KRX_BASE_URL}/{endpoint}",
            params={"basDd": _ymd(base_date)},
            headers={"AUTH_KEY": api_key, "Accept": "application/json"},
            timeout=timeout,
        )
        items = _ensure_list(payload.get("OutBlock_1") or payload.get("output") or payload.get("data"))
        row = _select_representative_index(items, asset_type)
        if not row:
            continue
        price = _to_float(row.get("CLSPRC_IDX") or row.get("clsprcIdx") or row.get("close") or row.get("종가"))
        if price <= 0:
            continue
        return [
            MarketPriceRow(
                asset_type=asset_type,
                base_date=base_date,
                price=price,
                change_rate=_to_float(row.get("FLUC_RT") or row.get("flucRt") or row.get("등락률")),
                source=SOURCE_KRX,
                source_meta={"endpoint": endpoint, "index_name": row.get("IDX_NM") or row.get("idxNm")},
            )
        ]
    return []


def _select_representative_index(items: list[dict[str, Any]], asset_type: str) -> dict[str, Any] | None:
    wanted_class = "KOSPI" if asset_type == "kospi" else "KOSDAQ"
    wanted_name = "코스피" if asset_type == "kospi" else "코스닥"
    for item in items:
        index_class = str(item.get("IDX_CLSS") or item.get("idxClss") or "").upper()
        name = str(item.get("IDX_NM") or item.get("idxNm") or item.get("지수명") or "").strip()
        if index_class == wanted_class and name == wanted_name and _to_float(item.get("CLSPRC_IDX")) > 0:
            return item
    for item in items:
        name = str(item.get("IDX_NM") or item.get("idxNm") or item.get("지수명") or "").upper()
        if name == wanted_class and _to_float(item.get("CLSPRC_IDX")) > 0:
            return item
    for item in items:
        name = str(item.get("IDX_NM") or item.get("idxNm") or item.get("지수명") or "").upper()
        if wanted_class in name and _to_float(item.get("CLSPRC_IDX")) > 0:
            return item
    for item in items:
        if _to_float(item.get("CLSPRC_IDX")) > 0:
            return item
    return None


def _normalize_exchange_payload(payload: Any, base_date: date) -> list[MarketPriceRow]:
    if not isinstance(payload, list):
        return []
    wanted = {"USD": "usd_krw", "JPY(100)": "jpy_krw", "EUR": "eur_krw", "CNH": "cnh_krw"}
    rows = []
    for item in payload:
        unit = str(item.get("cur_unit") or "").strip()
        asset_type = wanted.get(unit)
        if not asset_type:
            continue
        price = _to_float(item.get("deal_bas_r"))
        if price <= 0:
            continue
        rows.append(
            MarketPriceRow(
                asset_type=asset_type,
                base_date=base_date,
                price=price,
                source=SOURCE_EXCHANGE,
                source_meta={
                    "unit": "KRW",
                    "currency": unit,
                    "currency_name": item.get("cur_nm"),
                    "book_price": item.get("bkpr"),
                },
            )
        )
    return rows


def _with_computed_change(rows: list[MarketPriceRow]) -> list[MarketPriceRow]:
    computed = []
    previous: MarketPriceRow | None = None
    for row in rows:
        change_rate = row.change_rate
        if previous and previous.price:
            change_rate = round(((row.price - previous.price) / previous.price) * 100, 4)
        computed.append(
            MarketPriceRow(
                asset_type=row.asset_type,
                base_date=row.base_date,
                price=row.price,
                change_rate=change_rate,
                source=row.source,
                source_meta=row.source_meta,
            )
        )
        previous = row
    return computed


def _request_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _request_text(url: str, *, params: dict[str, Any], timeout: int = 30) -> str:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.text


def _ensure_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _parse_yyyymmdd(value: Any) -> date | None:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError:
        return None


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _to_float(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return 0
    try:
        return float(text)
    except ValueError:
        return 0


def _ymd(value: date) -> str:
    return value.strftime("%Y%m%d")
