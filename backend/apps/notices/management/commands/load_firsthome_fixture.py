from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from apps.fixture_store import load_fixture
from apps.notice_docs.services.analysis import analyze_notice_document
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload
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
            help="Analyze the representative fixture notice with the bundled sample PDF.",
        )

    def handle(self, *args, **options):
        data = load_fixture()

        HousingNotice.objects.all().delete()
        FinancialProduct.objects.all().delete()
        YouthPolicy.objects.all().delete()

        for notice in data["notices"]:
            classification = classify_notice_payload(notice)
            HousingNotice.objects.create(
                id=notice["id"],
                source_id=str(notice["id"]),
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
                source_url=notice.get("source_url", ""),
                tags=notice.get("tags", []),
                required_documents=notice.get("required_documents", []),
                cautions=notice.get("cautions", []),
                source_meta={"fixture_id": notice["id"]},
                ownership_type=notice.get("ownership_type") or classification.ownership_type,
                is_service_target=notice.get("is_service_target", classification.is_service_target),
                exclude_reason=notice.get("exclude_reason", classification.exclude_reason),
                official_document_status=notice.get("official_document_status", classification.official_document_status),
            )

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

        demo_message = ""
        if options["with_demo_analysis"]:
            demo_message = self._load_demo_analysis()

        self.stdout.write(
            self.style.SUCCESS(
                "Loaded FirstHome fixture: "
                f"{len(data['notices'])} notices, {len(data['products'])} products, {len(data['policies'])} policies."
                f"{demo_message}"
            )
        )

    def _load_demo_analysis(self) -> str:
        sample_pdf = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "public_sale_notice_611.pdf"
        if not sample_pdf.exists():
            return " Demo analysis skipped: sample PDF is missing."
        try:
            notice = HousingNotice.objects.get(id=101)
        except HousingNotice.DoesNotExist:
            return " Demo analysis skipped: notice #101 is missing."
        result = analyze_notice_document(notice, pdf_path=sample_pdf)
        return f" Demo analysis loaded for notice #101 with {len(result.get('unit_options', []))} option(s)."
