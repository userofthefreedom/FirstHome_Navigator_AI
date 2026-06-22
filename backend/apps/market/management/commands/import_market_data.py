from __future__ import annotations

import re
from datetime import date, timedelta

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.market.models import MarketAssetPrice
from apps.market.services.providers import (
    MarketDataError,
    MarketPriceRow,
    fetch_ecos_base_rate_rows,
    fetch_estate_trade_rows,
    fetch_exchange_rows,
    fetch_gold_rows,
    fetch_krx_index_rows,
    fetch_silver_rows,
    previous_month,
)


ESTATE_REGION_TARGETS = [
    ("11110", "서울 종로구"),
    ("11530", "서울 구로구"),
    ("11680", "서울 강남구"),
    ("26350", "부산 해운대구"),
    ("27260", "대구 수성구"),
    ("28237", "인천 부평구"),
    ("29140", "광주 서구"),
    ("30170", "대전 서구"),
    ("31140", "울산 남구"),
    ("36110", "세종시"),
    ("41117", "경기 수원시 영통구"),
    ("41135", "경기 성남시 분당구"),
    ("41450", "경기 하남시"),
    ("43111", "충북 청주시 상당구"),
    ("44133", "충남 천안시 서북구"),
    ("50110", "제주 제주시"),
]


class Command(BaseCommand):
    help = "Import compact Economy NOW market data from approved external APIs."

    ASSET_CHOICES = ["all", "gold", "silver", "exchange", "ecos", "krx", "estate"]

    def add_arguments(self, parser):
        parser.add_argument("--asset", choices=self.ASSET_CHOICES, default="all")
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="History window for date-range providers. Default keeps free API usage compact.",
        )
        parser.add_argument("--clear", action="store_true", help="Delete selected market rows before importing.")
        parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize rows without writing to DB.")

    def handle(self, *args, **options):
        days = max(1, options["days"])
        end = date.today()
        start = end - timedelta(days=days - 1)
        selected_assets = self._selected_assets(options["asset"])

        rows: list[MarketPriceRow] = []
        failures: list[str] = []

        for asset in selected_assets:
            try:
                asset_rows = self._fetch_asset(asset, start=start, end=end)
            except (requests.RequestException, MarketDataError, ValueError) as exc:
                failures.append(f"{asset}: {_safe_error(exc)}")
                continue
            rows.extend(asset_rows)
            self.stdout.write(f"{asset}: fetched {len(asset_rows)} row(s)")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(rows)} market rows. No database changes."))
            for row in rows[:10]:
                self.stdout.write(f"- {row.asset_type} {row.base_date.isoformat()} {row.price} {row.source}")
            self._write_failures(failures)
            return

        if options["clear"]:
            MarketAssetPrice.objects.filter(asset_type__in=self._asset_types_for_clear(selected_assets)).delete()

        created_count = 0
        updated_count = 0
        for row in rows:
            source_meta = row.source_meta or {}
            region_code = str(source_meta.get("lawd_cd") or source_meta.get("region_code") or "")
            region_name = str(source_meta.get("region_name") or source_meta.get("label") or "")
            if " 아파트 평균" in region_name:
                region_name = region_name.split(" 아파트 평균", 1)[0]
            _instance, created = MarketAssetPrice.objects.update_or_create(
                asset_type=row.asset_type,
                base_date=row.base_date,
                region_code=region_code,
                defaults={
                    "region_name": region_name,
                    "price": row.price,
                    "change_rate": row.change_rate,
                    "source": row.source,
                    "source_meta": source_meta,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported market rows: {created_count} created, {updated_count} updated."))
        self._write_failures(failures)

    def _fetch_asset(self, asset: str, *, start: date, end: date) -> list[MarketPriceRow]:
        keys = settings.EXTERNAL_API_KEYS
        if asset == "gold":
            api_key = self._required_key(keys, "DATA_GO_KR_SERVICE_KEY", "gold and estate")
            return fetch_gold_rows(api_key, start=start, end=end)
        if asset == "silver":
            api_key = self._required_key(keys, "METALS_DEV_API_KEY", "silver")
            return fetch_silver_rows(api_key, start=start, end=end)
        if asset == "exchange":
            api_key = self._required_key(keys, "KOREAEXIM_API_KEY", "exchange")
            rows: list[MarketPriceRow] = []
            for target_date in _business_days(start, end):
                try:
                    rows.extend(fetch_exchange_rows(api_key, target_date=target_date, timeout=10))
                except (requests.RequestException, MarketDataError, ValueError) as exc:
                    self.stderr.write(self.style.WARNING(f"Skipped exchange {target_date.isoformat()}: {_safe_error(exc)}"))
            return _unique_rows(rows)
        if asset == "ecos":
            api_key = self._required_key(keys, "BOK_ECOS_API_KEY", "ECOS")
            return fetch_ecos_base_rate_rows(api_key, start=start, end=end)
        if asset == "krx":
            api_key = self._required_key(keys, "KRX_API_KEY", "KRX")
            rows: list[MarketPriceRow] = []
            for target_date in _business_days(start, end):
                try:
                    rows.extend(fetch_krx_index_rows(api_key, target_date=target_date, timeout=15))
                except (requests.RequestException, MarketDataError, ValueError) as exc:
                    self.stderr.write(self.style.WARNING(f"Skipped krx {target_date.isoformat()}: {_safe_error(exc)}"))
            return _unique_rows(rows)
        if asset == "estate":
            api_key = self._required_key(keys, "DATA_GO_KR_SERVICE_KEY", "estate")
            rows: list[MarketPriceRow] = []
            for month in _months_between(start, previous_month(end)):
                for lawd_cd, region_name in ESTATE_REGION_TARGETS:
                    try:
                        rows.extend(fetch_estate_trade_rows(api_key, month=month, lawd_cd=lawd_cd, region_name=region_name, timeout=15))
                    except (requests.RequestException, MarketDataError, ValueError) as exc:
                        self.stderr.write(self.style.WARNING(f"Skipped estate {region_name} {month:%Y-%m}: {_safe_error(exc)}"))
            return _unique_rows(rows)
        raise CommandError(f"Unsupported asset: {asset}")

    def _selected_assets(self, asset: str) -> list[str]:
        if asset == "all":
            return ["gold", "silver", "exchange", "ecos", "krx", "estate"]
        return [asset]

    def _asset_types_for_clear(self, assets: list[str]) -> list[str]:
        mapping = {
            "gold": ["gold"],
            "silver": ["silver"],
            "exchange": ["usd_krw", "jpy_krw", "eur_krw", "cnh_krw", "gbp_krw", "aud_krw", "cad_krw"],
            "ecos": ["base_rate"],
            "krx": ["kospi", "kosdaq"],
            "estate": ["estate_apt_trade_avg"],
        }
        asset_types: list[str] = []
        for asset in assets:
            asset_types.extend(mapping[asset])
        return asset_types

    def _required_key(self, keys: dict, name: str, label: str) -> str:
        value = keys.get(name, "")
        if not value:
            raise MarketDataError(f"{name} is missing. Add it to backend/.env for {label}.")
        return value

    def _write_failures(self, failures: list[str]) -> None:
        for failure in failures:
            self.stderr.write(self.style.WARNING(f"Skipped {failure}"))


def _business_days(start: date, end: date):
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def _months_between(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    months: list[date] = []
    while current <= last:
        months.append(current)
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)
    return months


def _unique_rows(rows: list[MarketPriceRow]) -> list[MarketPriceRow]:
    unique: dict[tuple[str, date, str], MarketPriceRow] = {}
    for row in rows:
        meta = row.source_meta or {}
        region_code = str(meta.get("lawd_cd") or meta.get("region_code") or "")
        unique[(row.asset_type, row.base_date, region_code)] = row
    return sorted(unique.values(), key=lambda row: (row.asset_type, row.base_date))


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    message = re.sub(r"([?&](?:authkey|serviceKey)=)[^&\s)]+", r"\1***", message, flags=re.IGNORECASE)
    return message
