from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.fixture_store import load_fixture, seed_fixture_notice_analysis
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload
from apps.notices.services.map_locations import resolve_notice_location
from apps.policies.models import YouthPolicy
from apps.products.models import FinancialProduct


def parse_date(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value).date()


class Command(BaseCommand):
    help = "Load FirstHome MVP fixture data into the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-demo-analysis",
            action="store_true",
            help="Kept for compatibility. Fixture notices are seeded with analysis data by default.",
        )

    def handle(self, *args, **options):
        data = load_fixture()

        HousingNotice.objects.all().delete()
        FinancialProduct.objects.all().delete()
        YouthPolicy.objects.all().delete()

        for notice in data["notices"]:
            classification = classify_notice_payload(notice)
            location = resolve_notice_location(notice)
            instance = HousingNotice.objects.create(
                id=notice["id"],
                source_id=f"fixture-{notice['id']}",
                title=notice["title"],
                provider=notice["provider"],
                region=notice["region"],
                district=notice["district"],
                supply_type=notice["supply_type"],
                housing_type=notice["housing_type"],
                area=notice.get("area", ""),
                price=notice.get("price", 0),
                contract_rate=notice.get("contract_rate", 0.1),
                application_deadline=parse_date(notice.get("application_deadline")),
                winner_date=parse_date(notice.get("winner_date")),
                contract_date=parse_date(notice.get("contract_date")),
                move_in=notice.get("move_in", ""),
                competition=notice.get("competition", ""),
                source_url="",
                location_label=notice.get("location_label") or location["label"],
                latitude=Decimal(str(notice.get("latitude") or location["lat"])),
                longitude=Decimal(str(notice.get("longitude") or location["lng"])),
                geocode_quality=notice.get("geocode_quality") or location["quality"],
                tags=notice.get("tags", []),
                required_documents=notice.get("required_documents", []),
                cautions=notice.get("cautions", []),
                source_meta={"fixture_id": notice["id"], "fixture_notice": True},
                ownership_type=notice.get("ownership_type") or classification.ownership_type,
                is_service_target=notice.get("is_service_target", classification.is_service_target),
                exclude_reason=notice.get("exclude_reason", classification.exclude_reason),
                official_document_status="analyzed",
            )
            seed_fixture_notice_analysis(instance, notice)

        for product in data["products"]:
            FinancialProduct.objects.create(
                id=product["id"],
                name=product["name"],
                provider=product["provider"],
                category=product["category"],
                rate=product.get("rate", ""),
                monthly_limit=product.get("monthly_limit", 0),
                term_months=product.get("term_months", 0),
                protection_status=product.get("protection_status", True),
                source_url=product.get("source_url", ""),
                reasons=product.get("reasons", []),
            )

        for policy in data["policies"]:
            YouthPolicy.objects.create(
                id=policy["id"],
                name=policy["name"],
                provider=policy["provider"],
                target=policy["target"],
                benefit=policy.get("benefit", ""),
                policy_category=policy.get("policy_category", ""),
                regions=policy.get("regions", []),
                age_min=policy.get("age_min", 19),
                age_max=policy.get("age_max", 39),
                max_income=policy.get("max_income", 0),
                requires_homeless=policy.get("requires_homeless", False),
                source_url=policy.get("source_url", ""),
                reasons=policy.get("reasons", []),
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Loaded FirstHome fixture: "
                f"{len(data['notices'])} notices, {len(data['products'])} products, {len(data['policies'])} policies."
                " Fixture analysis data loaded for every notice."
            )
        )
