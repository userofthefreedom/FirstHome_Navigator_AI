from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.products.models import FinancialProduct
from apps.products.services.finlife import fetch_all_finlife_products


class Command(BaseCommand):
    help = "Import deposit and saving products from the FSS Finlife API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--kind",
            choices=["deposit", "saving", "both"],
            default="both",
            help="Which Finlife product type to import.",
        )
        parser.add_argument(
            "--top-fin-grp-no",
            default="020000",
            help="Finlife financial group code. 020000 means banks.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing financial products before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and normalize products without writing to the database.",
        )

    def handle(self, *args, **options):
        api_key = settings.EXTERNAL_API_KEYS.get("FINLIFE_API_KEY", "")
        if not api_key:
            raise CommandError("FINLIFE_API_KEY is missing. Add it to backend/.env.")

        kinds = ["deposit", "saving"] if options["kind"] == "both" else [options["kind"]]
        products = fetch_all_finlife_products(
            api_key,
            kinds=kinds,
            top_fin_grp_no=options["top_fin_grp_no"],
        )

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(products)} Finlife products. No database changes."))
            self.stdout.write(self._summary_line(products))
            for product in products[:5]:
                self.stdout.write(f"- {product.provider} {product.name} {product.rate}")
            return

        if options["clear"]:
            FinancialProduct.objects.all().delete()

        created_count = 0
        updated_count = 0
        for product in products:
            _instance, created = FinancialProduct.objects.update_or_create(
                provider=product.provider,
                name=product.name,
                category=product.category,
                defaults={
                    "rate": product.rate,
                    "monthly_limit": product.monthly_limit,
                    "term_months": product.term_months,
                    "protection_status": product.protection_status,
                    "source_url": product.source_url,
                    "reasons": product.reasons,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported Finlife products: {created_count} created, {updated_count} updated."
            )
        )
        self.stdout.write(self._summary_line(products))

    def _summary_line(self, products):
        deposit_count = sum(1 for product in products if product.category == "예금")
        saving_count = sum(1 for product in products if product.category == "적금")
        protected_count = sum(1 for product in products if product.protection_status)
        return f"Summary: {deposit_count} deposits, {saving_count} savings, {protected_count} protected products."
