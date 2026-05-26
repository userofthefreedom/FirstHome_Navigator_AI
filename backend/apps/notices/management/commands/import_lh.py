from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload
from apps.notices.services.lh import fetch_all_lh_notices, fetch_lh_supply_payload, supply_info_summary


class Command(BaseCommand):
    help = "Import LH housing notices from data.go.kr."

    def add_arguments(self, parser):
        parser.add_argument("--page-size", type=int, default=100)
        parser.add_argument(
            "--max-pages",
            type=int,
            default=5,
            help="Maximum pages to fetch. Use 0 to fetch every page.",
        )
        parser.add_argument("--clear", action="store_true", help="Delete existing notices before importing.")
        parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize notices without writing to DB.")
        parser.add_argument(
            "--service-target-only",
            action="store_true",
            help="Persist only ownership-sale notices that are in the FirstHome service scope.",
        )
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
            service_target_count = sum(1 for notice in notices if self._classification(notice).is_service_target)
            missing_price_count = sum(
                1
                for notice in notices
                if self._notice_price(notice, supply_summaries.get(notice.source_id, {})) <= 0
            )
            missing_target_price_count = sum(
                1
                for notice in notices
                if self._classification(notice).is_service_target
                and self._notice_price(notice, supply_summaries.get(notice.source_id, {})) <= 0
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fetched {len(notices)} LH housing notices. "
                    f"{service_target_count} service-target sale notices. "
                    f"{missing_price_count} need official price checks "
                    f"({missing_target_price_count} service-target). No database changes."
                )
            )
            preview_notices = self._supply_target_order(notices)[:5] if options["service_target_only"] else notices[:5]
            for notice in preview_notices:
                summary = supply_summaries.get(notice.source_id, {})
                target_mark = "sale" if self._classification(notice).is_service_target else "skip"
                price = self._notice_price(notice, summary)
                price_label = f"{price:,}원" if price else "price pending"
                self.stdout.write(
                    f"- [{target_mark}] {notice.region} {notice.supply_type} "
                    f"{notice.title} ({summary.get('area', notice.area)}, {price_label})"
                )
            return

        if options["clear"]:
            HousingNotice.objects.all().delete()

        created_count = 0
        updated_count = 0
        skipped_count = 0
        missing_price_count = 0
        for notice in notices:
            summary = supply_summaries.get(notice.source_id, {})
            price = self._notice_price(notice, summary)
            defaults = {
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
            }
            classification = classify_notice_payload({**defaults, "provider": notice.provider, "source_id": notice.source_id})
            if options["service_target_only"] and not classification.is_service_target:
                skipped_count += 1
                continue
            if price <= 0:
                missing_price_count += 1
            instance, created = HousingNotice.objects.update_or_create(
                provider=notice.provider,
                source_id=notice.source_id,
                defaults={
                    **defaults,
                    "ownership_type": classification.ownership_type,
                    "is_service_target": classification.is_service_target,
                    "exclude_reason": classification.exclude_reason,
                },
            )
            if classification.is_service_target:
                self._sync_supply_options(instance, summary)
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported LH notices: {created_count} created, {updated_count} updated, "
                f"{skipped_count} skipped, {missing_price_count} need official price checks."
            )
        )

    def _fetch_supply_summaries(self, api_key, notices, options):
        limit = options["supply_limit"]
        selected_notices = self._supply_target_order(notices)
        selected_notices = selected_notices if limit == 0 else selected_notices[:limit]
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

    def _sync_supply_options(self, notice, summary):
        rows = summary.get("unit_options") if isinstance(summary, dict) else None
        if not rows or notice.official_document_status == "analyzed":
            return

        seen_keys = set()
        for index, row in enumerate(rows, start=1):
            unit_type = str(row.get("unit_type") or "").strip()
            base_price = int(row.get("base_price") or 0)
            if not unit_type or base_price <= 0:
                continue
            seen_keys.add((unit_type, "전체", "basic"))
            option, _created = HousingUnitOption.objects.update_or_create(
                notice=notice,
                unit_type=unit_type,
                floor_group="전체",
                option_type="basic",
                defaults={
                    "document": None,
                    "extraction": None,
                    "exclusive_area_m2": float(row.get("exclusive_area_m2") or 0),
                    "base_price": base_price,
                    "loan_amount": 0,
                    "balcony_extension_price": 0,
                    "confidence": 0.5,
                    "source_page": 0,
                    "source_text": (
                        "LH 공급정보 API: "
                        f"{row.get('raw_unit_type') or unit_type}, "
                        f"평균분양가격 {base_price:,}원"
                    ),
                },
            )
            self._replace_supply_payment_schedule(option, notice, base_price, index)

        if seen_keys:
            for option in HousingUnitOption.objects.filter(
                notice=notice,
                document__isnull=True,
                extraction__isnull=True,
                source_text__startswith="LH 공급정보 API",
            ):
                key = (option.unit_type, option.floor_group, option.option_type)
                if key not in seen_keys:
                    option.delete()

    def _replace_supply_payment_schedule(self, option, notice, price, sequence_offset):
        option.payment_schedules.all().delete()
        down_payment = round(price * float(notice.contract_rate or 0.1))
        middle_payment = round(price * 0.6)
        final_payment = max(0, price - down_payment - middle_payment)
        contract_date = notice.contract_date
        middle_date = contract_date + timedelta(days=180) if contract_date else None
        rows = [
            ("계약금", contract_date, down_payment, "down_payment", 1),
            ("중도금 계획 확인", middle_date, middle_payment, "middle_payment", 2),
            ("잔금 계획 확인", None, final_payment, "final_payment", 3),
        ]
        for label, due_date, amount, payment_type, sequence in rows:
            PaymentSchedule.objects.create(
                unit_option=option,
                label=label,
                due_date=due_date,
                amount=amount,
                payment_type=payment_type,
                sequence=sequence + sequence_offset * 10,
                evidence_text="LH 공급정보 API 기반 임시 계산값입니다. 실제 납부 조건은 공식 PDF 분석으로 확인해야 합니다.",
            )

    def _supply_target_order(self, notices):
        service_targets = [notice for notice in notices if self._classification(notice).is_service_target]
        other_notices = [notice for notice in notices if not self._classification(notice).is_service_target]
        return service_targets + other_notices

    def _classification(self, notice):
        return classify_notice_payload(
            {
                "title": notice.title,
                "provider": notice.provider,
                "district": notice.district,
                "supply_type": notice.supply_type,
                "housing_type": notice.housing_type,
                "tags": notice.tags,
                "source_meta": notice.source_meta,
            }
        )
