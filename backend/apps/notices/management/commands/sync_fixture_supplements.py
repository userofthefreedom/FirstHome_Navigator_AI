from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.fixture_store import sync_fixture_supplements
from apps.rules.cache_service import clear_firsthome_cache


class Command(BaseCommand):
    help = "Materialize only the fixture notices needed to supplement sparse real notice data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-per-region",
            type=int,
            default=None,
            help="Minimum active service-target notices per metropolitan region.",
        )

    def handle(self, *args, **options):
        fallback_settings = getattr(settings, "FIRSTHOME_FIXTURE_FALLBACK", {})
        if not fallback_settings.get("ENABLE_SUPPLEMENT", True):
            self.stdout.write(
                self.style.WARNING(
                    "FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=false, so no fixture supplements were materialized."
                )
            )
            return

        result = sync_fixture_supplements(min_per_region=options["min_per_region"])
        clear_firsthome_cache()

        self.stdout.write(
            self.style.SUCCESS(
                "Fixture supplement sync complete: "
                f"{result['before_count']} -> {result['after_count']} notices "
                f"(min_per_region={result['min_per_region']})."
            )
        )
        for region, counts in result["region_counts"].items():
            if counts["total"] < result["min_per_region"]:
                style = self.style.WARNING
            else:
                style = self.style.NOTICE
            self.stdout.write(
                style(
                    f"- {region}: total {counts['total']} "
                    f"(actual {counts['actual']}, fixture {counts['fixture']})"
                )
            )
