from __future__ import annotations

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
                failures.append(f"{asset}: {exc}")
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
            _instance, created = MarketAssetPrice.objects.update_or_create(
                asset_type=row.asset_type,
                base_date=row.base_date,
                defaults={
                    "price": row.price,
                    "change_rate": row.change_rate,
                    "source": row.source,
                    "source_meta": row.source_meta or {},
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
            return fetch_exchange_rows(api_key, target_date=end)
        if asset == "ecos":
            api_key = self._required_key(keys, "BOK_ECOS_API_KEY", "ECOS")
            return fetch_ecos_base_rate_rows(api_key, start=start, end=end)
        if asset == "krx":
            api_key = self._required_key(keys, "KRX_API_KEY", "KRX")
            return fetch_krx_index_rows(api_key, target_date=end)
        if asset == "estate":
            api_key = self._required_key(keys, "DATA_GO_KR_SERVICE_KEY", "estate")
            return fetch_estate_trade_rows(api_key, month=previous_month(end))
        raise CommandError(f"Unsupported asset: {asset}")

    def _selected_assets(self, asset: str) -> list[str]:
        if asset == "all":
            return ["gold", "silver", "exchange", "ecos", "krx", "estate"]
        return [asset]

    def _asset_types_for_clear(self, assets: list[str]) -> list[str]:
        mapping = {
            "gold": ["gold"],
            "silver": ["silver"],
            "exchange": ["usd_krw", "jpy_krw", "eur_krw", "cnh_krw"],
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
