from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import requests


LH_NOTICE_URL = "https://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"
LH_SUPPLY_INFO_URL = "https://apis.data.go.kr/B552555/lhLeaseNoticeSplInfo1/getLeaseNoticeSplInfo1"
EXCLUDE_KEYWORDS = ("토지", "상가", "주차장", "주유소", "산업시설", "근린생활")
HOUSING_KEYWORDS = ("주택", "임대", "분양", "행복", "국민", "영구", "매입", "전세", "공공")


@dataclass(frozen=True)
class LhNotice:
    source_id: str
    title: str
    provider: str
    region: str
    district: str
    supply_type: str
    housing_type: str
    area: str
    price: int
    contract_rate: float
    application_deadline: date
    winner_date: date
    contract_date: date
    move_in: str
    competition: str
    source_url: str
    tags: list[str]
    required_documents: list[str]
    cautions: list[str]
    source_meta: dict[str, Any]


def fetch_lh_payload(
    api_key: str,
    *,
    page: int = 1,
    page_size: int = 100,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    response = requests.get(
        LH_NOTICE_URL,
        params={"serviceKey": api_key, "PG_SZ": str(page_size), "PAGE": str(page)},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Unexpected LH API response shape.")
    return payload


def fetch_lh_supply_payload(
    api_key: str,
    *,
    pan_id: str,
    spl_inf_tp_cd: str = "",
    ccr_cnnt_sys_ds_cd: str = "",
    timeout: int = 10,
) -> list[dict[str, Any]]:
    params = {"serviceKey": api_key, "PAN_ID": pan_id}
    if spl_inf_tp_cd:
        params["SPL_INF_TP_CD"] = spl_inf_tp_cd
    if ccr_cnnt_sys_ds_cd:
        params["CCR_CNNT_SYS_DS_CD"] = ccr_cnnt_sys_ds_cd

    response = requests.get(LH_SUPPLY_INFO_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Unexpected LH supply API response shape.")
    return payload


def fetch_all_lh_notices(
    api_key: str,
    *,
    page_size: int = 100,
    max_pages: int = 3,
    timeout: int = 10,
) -> list[LhNotice]:
    notices: list[LhNotice] = []
    page = 1
    while True:
        payload = fetch_lh_payload(api_key, page=page, page_size=page_size, timeout=timeout)
        notices.extend(normalize_lh_notices(payload))

        total_count = _total_count(payload)
        if total_count <= page * page_size:
            break
        if max_pages and page >= max_pages:
            break
        page += 1
    return notices


def normalize_lh_notices(payload: list[dict[str, Any]]) -> list[LhNotice]:
    rows = _extract_rows(payload)
    notices: list[LhNotice] = []
    for row in rows:
        if not _is_housing_notice(row):
            continue
        deadline = _parse_date(row.get("CLSG_DT"))
        if deadline is None:
            continue

        title = str(row.get("PAN_NM") or "").strip()
        source_id = str(row.get("PAN_ID") or title).strip()
        source_url = str(row.get("DTL_URL") or row.get("DTL_URL_MOB") or "").strip()
        raw_supply_type = str(row.get("AIS_TP_CD_NM") or row.get("UPP_AIS_TP_NM") or "LH 공고").strip()
        region = _region_name(str(row.get("CNP_CD_NM") or "").strip())
        winner_date = deadline + timedelta(days=14)
        contract_date = deadline + timedelta(days=30)

        notices.append(
            LhNotice(
                source_id=source_id[:80],
                title=title[:120],
                provider="LH",
                region=region,
                district=str(row.get("CNP_CD_NM") or region or "공식 공고 확인").strip()[:80],
                supply_type=_supply_type(raw_supply_type, title),
                housing_type=raw_supply_type[:40],
                area="공식 공고 확인",
                price=0,
                contract_rate=0.1,
                application_deadline=deadline,
                winner_date=winner_date,
                contract_date=contract_date,
                move_in="공식 공고 확인",
                competition="LH 공고",
                source_url=source_url,
                tags=_tags(raw_supply_type, title, region),
                required_documents=["주민등록등본", "소득금액증명", "무주택 확인"],
                cautions=[
                    "LH API 목록 공고는 가격, 계약일, 세부 자격이 일부 생략될 수 있어 공식 공고문 확인이 필요합니다.",
                ],
                source_meta={
                    "pan_id": source_id,
                    "spl_inf_tp_cd": str(row.get("SPL_INF_TP_CD") or "").strip(),
                    "ccr_cnnt_sys_ds_cd": str(row.get("CCR_CNNT_SYS_DS_CD") or "").strip(),
                    "upp_ais_tp_cd": str(row.get("UPP_AIS_TP_CD") or "").strip(),
                    "ais_tp_cd": str(row.get("AIS_TP_CD") or "").strip(),
                },
            )
        )
    return notices


def _extract_rows(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for block in payload:
        rows = block.get("dsList")
        if isinstance(rows, list):
            return rows
    return []


def supply_info_summary(payload: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _extract_supply_rows(payload)
    if not rows:
        return {}

    areas = _unique_values(rows, ("DDO_AR", "SPL_AR", "SIL_AR"))
    prices = [
        amount
        for row in rows
        for key in ("LS_GMY", "RFE", "XPC_PR", "SPL_AMT", "LTTOT_TOP_AMOUNT")
        if (amount := _money(row.get(key))) > 0
    ]
    housing_types = _unique_values(rows, ("HTY_NNA", "SST_NM", "SBD_LGO_NM", "BZDT_NM"))
    districts = _unique_values(rows, ("SBD_LGO_NM", "BZDT_NM"))
    total_units = sum(_int_value(row.get("HSH_CNT") or row.get("OCNT")) for row in rows)

    summary: dict[str, Any] = {"supply_rows": len(rows)}
    if areas:
        summary["area"] = ", ".join(areas[:4])
    if prices:
        summary["price"] = max(prices)
    if housing_types:
        summary["housing_type"] = housing_types[0][:40]
    if districts:
        summary["district"] = districts[0][:80]
    if total_units:
        summary["competition"] = f"{total_units}호"
    return summary


def _extract_supply_rows(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block in payload:
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if key.startswith("dsList") and key != "dsList01Nm" and isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
    return rows


def _total_count(payload: list[dict[str, Any]]) -> int:
    rows = _extract_rows(payload)
    if not rows:
        return 0
    try:
        return int(rows[0].get("ALL_CNT") or len(rows))
    except (TypeError, ValueError):
        return len(rows)


def _is_housing_notice(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key) or "") for key in ["PAN_NM", "AIS_TP_CD_NM", "UPP_AIS_TP_NM"])
    if any(keyword in text for keyword in EXCLUDE_KEYWORDS):
        return False
    return any(keyword in text for keyword in HOUSING_KEYWORDS)


def _unique_values(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for key in keys:
            value = str(row.get(key) or "").strip()
            if value and value != "공고문 참조":
                values.append(value)
                break
    return list(dict.fromkeys(values))


def _money(value: Any) -> int:
    if value is None:
        return 0
    digits = "".join(char for char in str(value) if char.isdigit())
    if not digits:
        return 0
    return int(digits)


def _int_value(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y.%m.%d", "%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _region_name(value: str) -> str:
    if value.startswith("서울"):
        return "서울"
    if value.startswith("경기"):
        return "경기 남부"
    if value.startswith("인천"):
        return "인천"
    if value.startswith("부산"):
        return "부산"
    return value or "전국"


def _supply_type(raw_supply_type: str, title: str) -> str:
    text = f"{raw_supply_type} {title}"
    if "행복" in text or "청년" in text:
        return "청년 공공주택"
    if "분양" in text:
        return "공공분양"
    if "임대" in text or "전세" in text or "매입" in text:
        return "공공임대"
    return raw_supply_type[:40] or "LH 공고"


def _tags(raw_supply_type: str, title: str, region: str) -> list[str]:
    text = f"{raw_supply_type} {title}"
    tags = ["LH", region]
    if "청년" in text or "행복" in text:
        tags.append("청년")
    if "분양" in text:
        tags.append("공공분양")
    if "임대" in text:
        tags.append("공공임대")
    return list(dict.fromkeys(tag for tag in tags if tag))
