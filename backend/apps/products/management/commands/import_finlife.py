from __future__ import annotations

import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.products.models import FinancialProduct, FinancialProductOption, LoanProduct, UserJoinedProduct
from apps.products.services.finlife import FINLIFE_SOURCE_URL, fetch_all_finlife_loans, fetch_finlife_payload, normalize_finlife_product_records
from apps.rules.cache_service import clear_firsthome_cache


LEGACY_TERM_NAME_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<months>\d+)\s*개월\)\s*$")


class Command(BaseCommand):
    help = "Import financial and mortgage products from the FSS Finlife API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--kind",
            choices=["deposit", "saving", "mortgage", "both", "all"],
            default="all",
            help="Which Finlife product type to import. both means deposit+saving, all also includes mortgage loans.",
        )
        parser.add_argument(
            "--top-fin-grp-no",
            default="020000",
            help="Finlife financial group code. 020000 means banks.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing selected financial and loan products before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and normalize products without writing to the database.",
        )
        parser.add_argument(
            "--repair-only",
            action="store_true",
            help="Merge legacy term-suffixed products into product options without calling the Finlife API.",
        )

    def handle(self, *args, **options):
        if options["repair_only"]:
            repaired_count = self._repair_legacy_split_products()
            clear_firsthome_cache()
            self.stdout.write(self.style.SUCCESS(f"Merged {repaired_count} legacy split products into rate options."))
            return

        api_key = settings.EXTERNAL_API_KEYS.get("FINLIFE_API_KEY", "")
        if not api_key:
            raise CommandError("FINLIFE_API_KEY is missing. Add it to backend/.env.")

        product_kinds = self._product_kinds(options["kind"])
        loan_kinds = self._loan_kinds(options["kind"])
        product_records = []
        for product_kind in product_kinds:
            payload = fetch_finlife_payload(api_key, product_kind, top_fin_grp_no=options["top_fin_grp_no"])
            product_records.extend(normalize_finlife_product_records(payload.get("result", {}), product_kind))
        loans = (
            fetch_all_finlife_loans(
                api_key,
                kinds=loan_kinds,
                top_fin_grp_no=options["top_fin_grp_no"],
            )
            if loan_kinds
            else []
        )

        if options["dry_run"]:
            product_keys = {(record["provider"], record["name"], record["category"]) for record in product_records}
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(product_keys)} Finlife products, {len(product_records)} rate options, and {len(loans)} loan products. No database changes."))
            self.stdout.write(self._summary_line(product_records, loans))
            for record in product_records[:5]:
                option = record["option"]
                self.stdout.write(f"- {record['provider']} {record['name']} {option['save_trm']}m {option['intr_rate2']}%")
            for loan in loans[:5]:
                self.stdout.write(f"- {loan.provider} {loan.name} {loan.rate}")
            return

        if options["clear"]:
            if product_kinds:
                FinancialProduct.objects.all().delete()
            if loan_kinds:
                LoanProduct.objects.all().delete()

        created_count = 0
        updated_count = 0
        touched_products = set()
        option_count = 0
        for record in product_records:
            product, created = FinancialProduct.objects.update_or_create(
                provider=record["provider"],
                name=record["name"],
                category=record["category"],
                defaults={
                    "product_code": record["product_code"],
                    "bank_code": record["bank_code"],
                    "rate": "",
                    "monthly_limit": record["monthly_limit"],
                    "term_months": 0,
                    "protection_status": True,
                    "source_url": FINLIFE_SOURCE_URL,
                    "join_way": record["join_way"],
                    "special_condition": record["special_condition"],
                    "source_meta": record["source_meta"],
                    "reasons": [
                        "금융감독원 금융상품통합비교공시 API에서 수집한 예적금 상품입니다.",
                        f"가입 방법: {record['join_way'] or '금융회사 확인 필요'}",
                    ],
                },
            )
            option = record["option"]
            FinancialProductOption.objects.update_or_create(
                product=product,
                save_trm=option["save_trm"],
                intr_rate_type=option["intr_rate_type"],
                rsrv_type=option["rsrv_type"],
                defaults={
                    "intr_rate_type_nm": option["intr_rate_type_nm"],
                    "intr_rate": option["intr_rate"],
                    "intr_rate2": option["intr_rate2"],
                    "rsrv_type_nm": option["rsrv_type_nm"],
                    "source_meta": option["source_meta"],
                },
            )
            touched_products.add(product.id)
            option_count += 1
            if created:
                created_count += 1
            else:
                updated_count += 1

        repaired_count = self._repair_legacy_split_products()
        self._refresh_product_summaries(FinancialProduct.objects.filter(id__in=touched_products))
        loan_created_count = 0
        loan_updated_count = 0
        for loan in loans:
            _instance, created = LoanProduct.objects.update_or_create(
                provider=loan.provider,
                name=loan.name,
                category=loan.category,
                defaults={
                    "loan_purpose": loan.loan_purpose,
                    "description": loan.description,
                    "target": loan.target,
                    "rate": loan.rate,
                    "limit": loan.limit,
                    "limit_amount": loan.limit_amount,
                    "term": loan.term,
                    "term_years": loan.term_years,
                    "age_min": loan.age_min,
                    "age_max": loan.age_max,
                    "max_income": loan.max_income,
                    "max_price": loan.max_price,
                    "max_area_m2": loan.max_area_m2,
                    "requires_homeless": loan.requires_homeless,
                    "source_url": loan.source_url,
                    "reasons": loan.reasons,
                    "caveats": loan.caveats,
                },
            )
            if created:
                loan_created_count += 1
            else:
                loan_updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported Finlife products: {created_count} created, {updated_count} updated, "
                f"{option_count} rate options, {repaired_count} legacy split products merged. "
                f"Loan products: {loan_created_count} created, {loan_updated_count} updated."
            )
        )
        self.stdout.write(self._summary_line(product_records, loans))
        clear_firsthome_cache()

    def _product_kinds(self, kind: str) -> list[str]:
        if kind == "both":
            return ["deposit", "saving"]
        if kind == "all":
            return ["deposit", "saving"]
        if kind in {"deposit", "saving"}:
            return [kind]
        return []

    def _loan_kinds(self, kind: str) -> list[str]:
        if kind in {"mortgage", "all"}:
            return ["mortgage"]
        return []

    def _summary_line(self, products, loans):
        product_keys = {(product["provider"], product["name"], product["category"]) for product in products}
        deposit_count = sum(1 for _provider, _name, category in product_keys if category == "예금")
        saving_count = sum(1 for _provider, _name, category in product_keys if category == "적금")
        mortgage_count = sum(1 for loan in loans if loan.category == "주택담보대출")
        return f"Summary: {deposit_count} deposits, {saving_count} savings, {len(products)} rate options, {mortgage_count} mortgage loans."

    def _repair_legacy_split_products(self) -> int:
        repaired = 0
        legacy_products = list(
            FinancialProduct.objects.filter(category__in=["예금", "적금", "deposit", "saving"])
            .filter(name__regex=r"\([0-9]+개월\)\s*$")
            .prefetch_related("options")
        )
        for legacy in legacy_products:
            match = LEGACY_TERM_NAME_RE.match(legacy.name)
            if not match:
                continue
            base_name = match.group("name").strip()
            months = int(match.group("months") or legacy.term_months or 0)
            if not base_name or not months:
                continue
            product, _created = FinancialProduct.objects.get_or_create(
                provider=legacy.provider,
                name=base_name[:120],
                category=legacy.category,
                defaults={
                    "product_code": legacy.product_code,
                    "bank_code": legacy.bank_code,
                    "rate": legacy.rate,
                    "monthly_limit": legacy.monthly_limit,
                    "term_months": legacy.term_months,
                    "protection_status": legacy.protection_status,
                    "source_url": legacy.source_url,
                    "join_way": legacy.join_way,
                    "special_condition": legacy.special_condition,
                    "source_meta": legacy.source_meta,
                    "reasons": legacy.reasons,
                },
            )
            option = legacy.options.first()
            if option is None:
                rate = self._rate_number(legacy.rate)
                option, _option_created = FinancialProductOption.objects.get_or_create(
                    product=product,
                    save_trm=months,
                    intr_rate_type="",
                    rsrv_type="",
                    defaults={
                        "intr_rate_type_nm": "대표 금리",
                        "intr_rate": rate,
                        "intr_rate2": rate,
                        "source_meta": {"legacy_product_id": legacy.id},
                    },
                )
            else:
                option.product = product
                option.save()
            for joined in UserJoinedProduct.objects.filter(product=legacy).select_related("user"):
                existing = UserJoinedProduct.objects.filter(user=joined.user, product=product).first()
                if existing:
                    if not existing.memo and joined.memo:
                        existing.memo = joined.memo
                    if existing.selected_option is None:
                        existing.selected_option = option
                    existing.save(update_fields=["memo", "selected_option"])
                    joined.delete()
                else:
                    joined.product = product
                    joined.selected_option = option
                    joined.save(update_fields=["product", "selected_option"])
            legacy.delete()
            self._refresh_product_summaries(FinancialProduct.objects.filter(id=product.id))
            repaired += 1
        return repaired

    def _refresh_product_summaries(self, queryset) -> None:
        for product in queryset.prefetch_related("options"):
            best = max(product.options.all(), key=lambda item: (item.intr_rate2, item.intr_rate, item.save_trm), default=None)
            if best:
                product.rate = f"최고 연 {float(best.intr_rate2 or best.intr_rate):.2f}%"
                product.term_months = best.save_trm
                product.save(update_fields=["rate", "term_months", "updated_at"])

    def _rate_number(self, value) -> float:
        match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
        return float(match.group(0)) if match else 0.0
