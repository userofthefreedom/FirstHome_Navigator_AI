from __future__ import annotations

from datetime import date

from django.db.models import Avg, Count, Max, Min
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import COMMON_ERROR_RESPONSES, MARKET_ASSETS_RESPONSE, MARKET_SUMMARY_RESPONSE, TAGS
from apps.market.models import MarketAssetPrice


ASSET_LABELS = {
    "gold": "금",
    "silver": "은",
    "usd_krw": "원/달러",
    "jpy_krw": "원/엔(100)",
    "eur_krw": "원/유로",
    "cnh_krw": "원/위안",
    "gbp_krw": "원/파운드",
    "aud_krw": "원/호주달러",
    "cad_krw": "원/캐나다달러",
    "base_rate": "한국은행 기준금리",
    "kospi": "KOSPI",
    "kosdaq": "KOSDAQ",
    "estate_apt_trade_avg": "전국 아파트 평균 실거래가",
}

UNIT_BY_ASSET = {
    "gold": "원/g",
    "silver": "USD/toz",
    "usd_krw": "원",
    "jpy_krw": "원",
    "eur_krw": "원",
    "cnh_krw": "원",
    "gbp_krw": "원",
    "aud_krw": "원",
    "cad_krw": "원",
    "base_rate": "%",
    "kospi": "pt",
    "kosdaq": "pt",
    "estate_apt_trade_avg": "만원",
}

REGION_PREFIX_LABELS = {
    "11": "서울",
    "26": "부산",
    "27": "대구",
    "28": "인천",
    "29": "광주",
    "30": "대전",
    "31": "울산",
    "36": "세종",
    "41": "경기",
    "43": "충북",
    "44": "충남",
    "46": "전남",
    "47": "경북",
    "48": "경남",
    "50": "제주",
    "51": "강원",
    "52": "전북",
}


@extend_schema(
    tags=[TAGS["market"]],
    summary="시장 지표 시계열",
    description="금, 은, 환율, 기준금리, KOSPI/KOSDAQ, 부동산 거래 평균 등 Economy NOW 차트 데이터를 반환합니다.",
    parameters=[
        OpenApiParameter("asset", str, OpenApiParameter.QUERY, description="gold, silver, usd_krw, base_rate, kospi, kosdaq, estate_apt_trade_avg 등"),
        OpenApiParameter("region", str, OpenApiParameter.QUERY, description="부동산 지표의 법정동/지역 코드"),
        OpenApiParameter("region_prefix", str, OpenApiParameter.QUERY, description="부동산 지표의 광역 코드 prefix"),
        OpenApiParameter("start", str, OpenApiParameter.QUERY, description="YYYY-MM-DD 시작일"),
        OpenApiParameter("end", str, OpenApiParameter.QUERY, description="YYYY-MM-DD 종료일"),
    ],
    responses={200: MARKET_ASSETS_RESPONSE, **COMMON_ERROR_RESPONSES},
)
@api_view(["GET"])
def market_assets_view(request):
    asset = request.query_params.get("asset", "gold")
    region_code = str(request.query_params.get("region", "")).strip()
    region_prefix = str(request.query_params.get("region_prefix", "")).strip()
    start = _parse_date(request.query_params.get("start"))
    end = _parse_date(request.query_params.get("end"))
    if start and end and start > end:
        return Response({"detail": "시작일은 종료일보다 늦을 수 없습니다.", "items": []}, status=400)

    queryset = MarketAssetPrice.objects.filter(asset_type=asset)
    if asset == "estate_apt_trade_avg" and region_code:
        queryset = queryset.filter(region_code=region_code)
    elif asset == "estate_apt_trade_avg" and region_prefix:
        queryset = queryset.filter(region_code__startswith=region_prefix)
    if start:
        queryset = queryset.filter(base_date__gte=start)
    if end:
        queryset = queryset.filter(base_date__lte=end)

    if asset == "estate_apt_trade_avg" and not region_code:
        items = [_serialize_grouped_price(item, asset) for item in _estate_grouped_rows(queryset)]
    else:
        items = [_serialize_price(item) for item in queryset.order_by("base_date")]
    latest = items[-1] if items else None
    return Response(
        {
            "asset": asset,
            "label": _asset_label(asset, region_code, region_prefix),
            "unit": _asset_unit(asset, latest),
            "items": items,
            "regions": _estate_region_options() if asset == "estate_apt_trade_avg" else [],
            "source": latest["source"] if latest else "database",
            "is_fixture": False,
            "detail": "" if items else "수집된 실제 데이터가 없습니다. import_market_data 명령을 실행해 주세요.",
        }
    )


@extend_schema(
    tags=[TAGS["market"]],
    summary="시장 지표 요약",
    description="Economy NOW 상단 카드와 수집 데이터 범위/건수 요약을 반환합니다.",
    responses={200: MARKET_SUMMARY_RESPONSE},
)
@api_view(["GET"])
def market_summary_view(_request):
    cards = [
        _summary_card("gold", "금 가격", "KRX 금시장 99.99 1kg 종가"),
        _summary_card("silver", "은 가격", "Metals.dev 은 현물 가격"),
        _summary_card("usd_krw", "원/달러 환율", "한국수출입은행 현재환율"),
        _summary_card("base_rate", "기준금리", "한국은행 ECOS 기준금리"),
        _summary_card("kospi", "KOSPI", "KRX Open API 지수 일별시세"),
        _summary_card("estate_apt_trade_avg", "부동산 거래", "국토교통부 아파트 실거래 월평균"),
    ]
    return Response({"cards": cards, "stats": _market_stats()})


def _summary_card(asset_type: str, label: str, description: str) -> dict:
    if asset_type == "estate_apt_trade_avg":
        return _estate_summary_card(label, description)
    item = MarketAssetPrice.objects.filter(asset_type=asset_type).order_by("-base_date").first()
    if not item:
        return {
            "asset": asset_type,
            "label": label,
            "value": "수집 필요",
            "description": description,
            "base_date": None,
            "source": "database",
            "change_rate": 0,
        }
    return {
        "asset": asset_type,
        "label": label,
        "value": _format_value(item),
        "description": f"{description} · {item.base_date.isoformat()}",
        "base_date": item.base_date.isoformat(),
        "source": item.source,
        "change_rate": item.change_rate,
    }


def _serialize_price(item: MarketAssetPrice) -> dict:
    return {
        "date": item.base_date.isoformat(),
        "price": item.price,
        "change_rate": item.change_rate,
        "source": item.source,
        "region_code": item.region_code,
        "region_name": item.region_name,
        "source_meta": item.source_meta,
        "unit": _asset_unit(item.asset_type, {"source_meta": item.source_meta}),
    }


def _serialize_grouped_price(item: dict, asset_type: str) -> dict:
    return {
        "date": item["base_date"].isoformat(),
        "price": round(float(item["price"] or 0), 2),
        "change_rate": 0,
        "source": "database",
        "region_code": "",
        "region_name": "전체",
        "source_meta": {"unit": UNIT_BY_ASSET.get(asset_type, ""), "deal_count": item.get("deal_count", 0)},
        "unit": UNIT_BY_ASSET.get(asset_type, ""),
    }


def _estate_grouped_rows(queryset):
    return queryset.values("base_date").annotate(price=Avg("price"), deal_count=Count("id")).order_by("base_date")


def _estate_summary_card(label: str, description: str) -> dict:
    latest_date = (
        MarketAssetPrice.objects.filter(asset_type="estate_apt_trade_avg")
        .aggregate(latest=Max("base_date"))
        .get("latest")
    )
    if not latest_date:
        return {
            "asset": "estate_apt_trade_avg",
            "label": label,
            "value": "수집 필요",
            "description": description,
            "base_date": None,
            "source": "database",
            "change_rate": 0,
        }
    aggregate = MarketAssetPrice.objects.filter(asset_type="estate_apt_trade_avg", base_date=latest_date).aggregate(
        price=Avg("price"),
        region_count=Count("region_code", distinct=True),
    )
    price = float(aggregate.get("price") or 0)
    region_count = int(aggregate.get("region_count") or 0)
    return {
        "asset": "estate_apt_trade_avg",
        "label": label,
        "value": f"{price:,.0f}{UNIT_BY_ASSET['estate_apt_trade_avg']}",
        "description": f"{description} · {latest_date.isoformat()} · {max(region_count, 1)}개 지역",
        "base_date": latest_date.isoformat(),
        "source": "database",
        "change_rate": 0,
    }


def _estate_region_options() -> list[dict]:
    rows = (
        MarketAssetPrice.objects.filter(asset_type="estate_apt_trade_avg")
        .exclude(region_code="")
        .values("region_code", "region_name")
        .annotate(count=Count("id"), first=Min("base_date"), last=Max("base_date"))
        .order_by("region_name", "region_code")
    )
    return [
        {
            "code": row["region_code"],
            "name": row["region_name"] or row["region_code"],
            "count": row["count"],
            "first": row["first"].isoformat() if row["first"] else "",
            "last": row["last"].isoformat() if row["last"] else "",
        }
        for row in rows
    ]


def _market_stats() -> list[dict]:
    rows = (
        MarketAssetPrice.objects.order_by()
        .values("asset_type")
        .annotate(count=Count("id"), first=Min("base_date"), last=Max("base_date"))
        .order_by("asset_type")
    )
    return [
        {
            "asset": row["asset_type"],
            "label": ASSET_LABELS.get(row["asset_type"], row["asset_type"]),
            "count": row["count"],
            "first": row["first"].isoformat() if row["first"] else "",
            "last": row["last"].isoformat() if row["last"] else "",
        }
        for row in rows
    ]


def _format_value(item: MarketAssetPrice) -> str:
    unit = _asset_unit(item.asset_type, {"source_meta": item.source_meta})
    if item.asset_type == "base_rate":
        return f"{item.price:.2f}{unit}"
    if item.asset_type in {
        "gold",
        "usd_krw",
        "jpy_krw",
        "eur_krw",
        "cnh_krw",
        "gbp_krw",
        "aud_krw",
        "cad_krw",
        "estate_apt_trade_avg",
    }:
        return f"{item.price:,.0f}{unit}"
    return f"{item.price:,.2f}{unit}"


def _asset_unit(asset_type: str, item: dict | None) -> str:
    meta = (item or {}).get("source_meta") or {}
    return str(meta.get("unit") or UNIT_BY_ASSET.get(asset_type, ""))


def _asset_label(asset_type: str, region_code: str = "", region_prefix: str = "") -> str:
    if asset_type != "estate_apt_trade_avg":
        return ASSET_LABELS.get(asset_type, asset_type)
    if not region_code and region_prefix:
        return f"{REGION_PREFIX_LABELS.get(region_prefix, region_prefix)} 아파트 평균 실거래가"
    if not region_code:
        return ASSET_LABELS.get(asset_type, asset_type)
    region = (
        MarketAssetPrice.objects.filter(asset_type=asset_type, region_code=region_code)
        .exclude(region_name="")
        .values_list("region_name", flat=True)
        .first()
    )
    return f"{region or region_code} 아파트 평균 실거래가"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
