from __future__ import annotations

from datetime import date

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.market.models import MarketAssetPrice


ASSET_LABELS = {
    "gold": "금",
    "silver": "은",
    "usd_krw": "원/달러",
    "jpy_krw": "원/엔(100)",
    "eur_krw": "원/유로",
    "cnh_krw": "원/위안",
    "base_rate": "한국은행 기준금리",
    "kospi": "KOSPI",
    "kosdaq": "KOSDAQ",
    "estate_apt_trade_avg": "서울 종로구 아파트 평균 실거래가",
}

UNIT_BY_ASSET = {
    "gold": "원/g",
    "silver": "USD/toz",
    "usd_krw": "원",
    "jpy_krw": "원",
    "eur_krw": "원",
    "cnh_krw": "원",
    "base_rate": "%",
    "kospi": "pt",
    "kosdaq": "pt",
    "estate_apt_trade_avg": "만원",
}


@api_view(["GET"])
def market_assets_view(request):
    asset = request.query_params.get("asset", "gold")
    start = _parse_date(request.query_params.get("start"))
    end = _parse_date(request.query_params.get("end"))
    if start and end and start > end:
        return Response({"detail": "시작일은 종료일보다 늦을 수 없습니다.", "items": []}, status=400)

    queryset = MarketAssetPrice.objects.filter(asset_type=asset)
    if start:
        queryset = queryset.filter(base_date__gte=start)
    if end:
        queryset = queryset.filter(base_date__lte=end)

    items = [_serialize_price(item) for item in queryset.order_by("base_date")]
    latest = items[-1] if items else None
    return Response(
        {
            "asset": asset,
            "label": ASSET_LABELS.get(asset, asset),
            "unit": _asset_unit(asset, latest),
            "items": items,
            "source": latest["source"] if latest else "database",
            "is_fixture": False,
            "detail": "" if items else "수집된 실제 데이터가 없습니다. import_market_data 명령을 실행해 주세요.",
        }
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
    return Response({"cards": cards})


def _summary_card(asset_type: str, label: str, description: str) -> dict:
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
        "source_meta": item.source_meta,
        "unit": _asset_unit(item.asset_type, {"source_meta": item.source_meta}),
    }


def _format_value(item: MarketAssetPrice) -> str:
    unit = _asset_unit(item.asset_type, {"source_meta": item.source_meta})
    if item.asset_type == "base_rate":
        return f"{item.price:.2f}{unit}"
    if item.asset_type in {"gold", "usd_krw", "jpy_krw", "eur_krw", "cnh_krw", "estate_apt_trade_avg"}:
        return f"{item.price:,.0f}{unit}"
    return f"{item.price:,.2f}{unit}"


def _asset_unit(asset_type: str, item: dict | None) -> str:
    meta = (item or {}).get("source_meta") or {}
    return str(meta.get("unit") or UNIT_BY_ASSET.get(asset_type, ""))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
