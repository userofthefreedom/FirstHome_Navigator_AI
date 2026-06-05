from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.notices.models import HousingNotice
from apps.notices.services.map_locations import kakao_geocode


class Command(BaseCommand):
    help = "Fill missing notice coordinates with Kakao Local REST API."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=30)
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        queryset = HousingNotice.objects.order_by("application_deadline", "id")
        if not options["overwrite"]:
            queryset = queryset.filter(latitude__isnull=True, longitude__isnull=True)
        if options["limit"] > 0:
            queryset = queryset[: options["limit"]]

        updated = 0
        checked = 0
        for notice in queryset:
            checked += 1
            query = _notice_query(notice)
            try:
                result = kakao_geocode(query)
            except Exception as exc:
                raise CommandError(f"Kakao geocoding failed for {notice.id}: {exc}") from exc
            if not result:
                self.stdout.write(f"- skip {notice.id}: {query}")
                continue
            self.stdout.write(
                f"- {'would update' if options['dry_run'] else 'update'} {notice.id}: "
                f"{query} -> {result['label']} ({result['lat']}, {result['lng']})"
            )
            if options["dry_run"]:
                continue
            notice.latitude = Decimal(str(result["lat"]))
            notice.longitude = Decimal(str(result["lng"]))
            notice.location_label = result["label"][:120]
            notice.geocode_quality = result["quality"]
            notice.save(update_fields=["latitude", "longitude", "location_label", "geocode_quality", "updated_at"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Checked {checked} notices, updated {updated} locations."))


def _notice_query(notice: HousingNotice) -> str:
    source_meta = notice.source_meta if isinstance(notice.source_meta, dict) else {}
    for key in ("address", "location_address", "location_label"):
        if source_meta.get(key):
            return str(source_meta[key])
    if notice.location_label:
        return notice.location_label
    return f"{notice.region} {notice.district}".strip()
