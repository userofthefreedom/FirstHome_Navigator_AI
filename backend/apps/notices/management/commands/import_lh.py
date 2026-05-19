from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notices.models import HousingNotice
from apps.notices.services.lh import fetch_all_lh_notices, fetch_lh_supply_payload, supply_info_summary


class Command(BaseCommand):
    help = "Import LH housing notices from data.go.kr."

    def add_arguments(self, parser):
        parser.add_argument("--page-size", type=int, default=100)
        parser.add_argument(
            "--max-pages",
            type=int,
            default=3,
            help="Maximum pages to fetch. Use 0 to fetch every page.",
        )
        parser.add_argument("--clear", action="store_true", help="Delete existing notices before importing.")
        parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize notices without writing to DB.")
        parser.add_argument(
            "--with-supply-info",
            action="store_true",
            help="Fetch LH supply detail rows and enrich area, price, and housing type when possible.",
        )
        parser.add_argument(
            "--supply-limit",
            type=int,
            default=30,
            help="Maximum notices to enrich with LH supply detail rows. Use 0 for every notice.",
        )

    def handle(self, *args, **options):
        api_key = settings.EXTERNAL_API_KEYS.get("DATA_GO_KR_SERVICE_KEY", "")
        if not api_key:
            raise CommandError("DATA_GO_KR_SERVICE_KEY is missing. Add it to backend/.env.")

        notices = fetch_all_lh_notices(
            api_key,
            page_size=options["page_size"],
            max_pages=options["max_pages"],
        )
        supply_summaries = self._fetch_supply_summaries(api_key, notices, options) if options["with_supply_info"] else {}

        if options["dry_run"]:
            missing_price_count = sum(
                1
                for notice in notices
                if self._notice_price(notice, supply_summaries.get(notice.source_id, {})) <= 0
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fetched {len(notices)} LH housing notices. "
                    f"{missing_price_count} need official price checks. No database changes."
                )
            )
            for notice in notices[:5]:
                summary = supply_summaries.get(notice.source_id, {})
                self.stdout.write(f"- {notice.region} {notice.supply_type} {notice.title} ({summary.get('area', notice.area)})")
            return

        if options["clear"]:
            HousingNotice.objects.all().delete()

        created_count = 0
        updated_count = 0
        missing_price_count = 0
        for notice in notices:
            summary = supply_summaries.get(notice.source_id, {})
            price = self._notice_price(notice, summary)
            if price <= 0:
                missing_price_count += 1
            _instance, created = HousingNotice.objects.update_or_create(
                provider=notice.provider,
                source_id=notice.source_id,
                defaults={
                    "title": notice.title,
                    "region": notice.region,
                    "district": summary.get("district", notice.district),
                    "supply_type": notice.supply_type,
                    "housing_type": summary.get("housing_type", notice.housing_type),
                    "area": summary.get("area", notice.area),
                    "price": price,
                    "contract_rate": notice.contract_rate,
                    "application_deadline": notice.application_deadline,
                    "winner_date": notice.winner_date,
                    "contract_date": notice.contract_date,
                    "move_in": notice.move_in,
                    "competition": summary.get("competition", notice.competition),
                    "source_url": notice.source_url,
                    "tags": notice.tags,
                    "required_documents": notice.required_documents,
                    "cautions": notice.cautions,
                    "source_meta": {**notice.source_meta, "supply_summary": summary} if summary else notice.source_meta,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported LH notices: {created_count} created, {updated_count} updated, "
                f"{missing_price_count} need official price checks."
            )
        )

    def _fetch_supply_summaries(self, api_key, notices, options):
        limit = options["supply_limit"]
        selected_notices = notices if limit == 0 else notices[:limit]
        summaries = {}
        for notice in selected_notices:
            meta = notice.source_meta
            if not meta.get("pan_id"):
                continue
            payload = fetch_lh_supply_payload(
                api_key,
                pan_id=meta["pan_id"],
                spl_inf_tp_cd=meta.get("spl_inf_tp_cd", ""),
                ccr_cnnt_sys_ds_cd=meta.get("ccr_cnnt_sys_ds_cd", ""),
            )
            summary = supply_info_summary(payload)
            if summary:
                summaries[notice.source_id] = summary
        return summaries

    def _notice_price(self, notice, summary):
        return int(summary.get("price") or notice.price or 0)
