from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import requests


YOUTHCENTER_POLICY_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
YOUTHCENTER_SOURCE_URL = "https://www.youthcenter.go.kr/cmnFooter/openapiIntro/oaiDoc/46"
REGION_NAMES = (
    "서울",
    "서울특별시",
    "부산",
    "부산광역시",
    "대구",
    "대구광역시",
    "인천",
    "인천광역시",
    "광주",
    "광주광역시",
    "대전",
    "대전광역시",
    "울산",
    "울산광역시",
    "세종",
    "세종특별자치시",
    "경기",
    "경기도",
    "강원",
    "강원도",
    "강원특별자치도",
    "충북",
    "충청북도",
    "충남",
    "충청남도",
    "전북",
    "전라북도",
    "전북특별자치도",
    "전남",
    "전라남도",
    "경북",
    "경상북도",
    "경남",
    "경상남도",
    "제주",
    "제주도",
    "제주특별자치도",
)
REGION_CANONICAL_NAMES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원도": "강원",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전라북도": "전북",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주도": "제주",
    "제주특별자치도": "제주",
}


class YouthCenterApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class YouthCenterPolicy:
    name: str
    provider: str
    target: str
    benefit: str
    policy_category: str
    regions: list[str]
    age_min: int
    age_max: int
    max_income: int
    requires_homeless: bool
    source_url: str
    reasons: list[str]


def fetch_youthcenter_payload(
    api_key: str,
    *,
    page: int = 1,
    display: int = 100,
    query: str = "",
    keyword: str = "",
    timeout: int = 10,
) -> Any:
    params = {
        "apiKeyNm": api_key,
        "apiSn": "86",
        "pageNum": str(page),
        "pageSize": str(display),
    }
    if query:
        params["query"] = query
    if keyword:
        params["keyword"] = keyword

    try:
        response = requests.get(
            YOUTHCENTER_POLICY_URL,
            params=params,
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise YouthCenterApiError(f"Ontong Youth API request failed: {exc.__class__.__name__}") from exc

    if response.is_redirect:
        location = response.headers.get("Location", "")
        if ":8080" in location:
            raise YouthCenterApiError(
                "Ontong Youth API redirected to port 8080, which is not reachable from this environment."
            )
        raise YouthCenterApiError("Ontong Youth API returned an unexpected redirect.")

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise YouthCenterApiError(f"Ontong Youth API returned HTTP {response.status_code}.") from exc
    return _decode_payload(response.text)


def normalize_youthcenter_policies(payload: Any) -> list[YouthCenterPolicy]:
    rows = _extract_rows(payload)
    policies: list[YouthCenterPolicy] = []
    for row in rows:
        name = _first(row, "plcyNm", "polyBizSjnm", "policyName", "bizNm")
        if not name:
            continue

        provider = _first(row, "sprvsnInstCdNm", "cnsgNmor", "operInstCdNm", "provider") or "온통청년"
        benefit = _first(row, "plcySprtCn", "sporCn", "benefit", "plcyExplnCn", "cn")
        target = _first(row, "sprtTrgtCn", "ageInfo", "target", "rqutPrdCn") or "공식 정책 상세 확인"
        category = _first(row, "lclsfNm", "mclsfNm", "bizTycdNm", "polyRlmCdNm") or "청년정책"
        source_url = _first(row, "plcyUrl", "aplyUrlAddr", "refUrlAddr1", "url") or YOUTHCENTER_SOURCE_URL
        age_text = " ".join([target, _first(row, "ageInfo", "sprtTrgtCn")])
        age_min, age_max = _age_range(row, age_text)
        max_income = _income_limit(_first(row, "earnCndCn", "income", "incomeInfo", "earnInfo"))

        policies.append(
            YouthCenterPolicy(
                name=name[:120],
                provider=provider[:60],
                target=target[:160],
                benefit=benefit,
                policy_category=category[:40],
                regions=_regions(" ".join(str(value) for value in row.values())),
                age_min=age_min,
                age_max=age_max,
                max_income=max_income,
                requires_homeless="무주택" in " ".join([target, benefit, name]),
                source_url=source_url,
                reasons=["온통청년 API 수집 정책", category[:40]],
            )
        )
    return policies


def _decode_payload(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    root = ET.fromstring(stripped)
    return _xml_to_dict(root)


def _xml_to_dict(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return element.text or ""
    grouped: dict[str, Any] = {}
    for child in children:
        value = _xml_to_dict(child)
        if child.tag in grouped:
            if not isinstance(grouped[child.tag], list):
                grouped[child.tag] = [grouped[child.tag]]
            grouped[child.tag].append(value)
        else:
            grouped[child.tag] = value
    return grouped


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("youthPolicyList", "policyList", "plcyList", "data", "items", "item", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            rows = _extract_rows(value)
            if rows:
                return rows
    return [payload] if _first(payload, "plcyNm", "polyBizSjnm", "policyName", "bizNm") else []


def _first(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _age_range(row: dict[str, Any], text: str) -> tuple[int, int]:
    min_age = _int(row.get("sprtTrgtMinAge") or row.get("minAge"))
    max_age = _int(row.get("sprtTrgtMaxAge") or row.get("maxAge"))
    if min_age and max_age:
        return min_age, max_age

    ages = [int(value) for value in re.findall(r"(\d{2})\s*세", text)]
    if len(ages) >= 2:
        return min(ages), max(ages)
    if len(ages) == 1:
        return 19, ages[0]
    return 19, 39


def _income_limit(text: str) -> int:
    match = re.search(r"(\d{2,5})\s*만\s*원", text)
    if match:
        return int(match.group(1)) * 10000
    return 0


def _regions(text: str) -> list[str]:
    regions = [REGION_CANONICAL_NAMES.get(region, region) for region in REGION_NAMES if region in text]
    regions = list(dict.fromkeys(regions))
    return regions or ["전국"]


def _int(value: Any) -> int:
    try:
        return int(str(value or "0").replace(",", ""))
    except ValueError:
        return 0
