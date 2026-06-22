from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.products.models import FinancialProduct, FinancialProductOption
from apps.products.services.finlife import FINLIFE_SOURCE_URL, fetch_finlife_payload
from apps.rules.cache_service import clear_firsthome_cache


class Command(BaseCommand):
    help = "Import deposit and saving products from the FSS Finlife API with separated options."

    def add_arguments(self, parser):
        parser.add_argument("--deposit-only", action="store_true")
        parser.add_argument("--saving-only", action="store_true")
        parser.add_argument("--top-fin-grp-no", default="020000")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        api_key = settings.EXTERNAL_API_KEYS.get("FINLIFE_API_KEY", "")
        if not api_key:
            raise CommandError("FINLIFE_API_KEY is missing. Add it to backend/.env.")

        kinds = self._kinds(options)
        records = []
        for kind in kinds:
            payload = fetch_finlife_payload(api_key, kind, top_fin_grp_no=options["top_fin_grp_no"])
            records.extend(_records_from_payload(payload.get("result", {}), kind))

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(records)} products/options. No database changes."))
            for record in records[:5]:
                self.stdout.write(f"- {record['provider']} {record['name']} {record['option']['save_trm']}m {record['option']['intr_rate2']}%")
            return

        if options["clear"]:
            FinancialProduct.objects.filter(category__in=["deposit", "saving"]).delete()

        touched_products = set()
        option_count = 0
        for record in records:
            product, _created = FinancialProduct.objects.update_or_create(
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

        for product in FinancialProduct.objects.filter(id__in=touched_products).prefetch_related("options"):
            best = max(product.options.all(), key=lambda item: (item.intr_rate2, item.intr_rate, item.save_trm), default=None)
            if best:
                product.rate = f"최고 연 {float(best.intr_rate2 or best.intr_rate):.2f}%"
                product.term_months = best.save_trm
                product.save(update_fields=["rate", "term_months", "updated_at"])

        clear_firsthome_cache()
        self.stdout.write(self.style.SUCCESS(f"Imported {len(touched_products)} products and {option_count} options."))

    def _kinds(self, options):
        if options["deposit_only"] and options["saving_only"]:
            raise CommandError("Use only one of --deposit-only or --saving-only.")
        if options["deposit_only"]:
            return ["deposit"]
        if options["saving_only"]:
            return ["saving"]
        return ["deposit", "saving"]


def _records_from_payload(result: dict, kind: str) -> list[dict]:
    category = "deposit" if kind == "deposit" else "saving"
    base_by_code = {item.get("fin_prdt_cd"): item for item in result.get("baseList") or []}
    records = []
    for option in result.get("optionList") or []:
        code = option.get("fin_prdt_cd")
        base = base_by_code.get(code) or {}
        provider = str(base.get("kor_co_nm") or "").strip()
        name = str(base.get("fin_prdt_nm") or "").strip()
        if not provider or not name:
            continue
        records.append(
            {
                "provider": provider[:60],
                "name": name[:120],
                "category": category,
                "product_code": str(code or "")[:80],
                "bank_code": str(base.get("fin_co_no") or "")[:40],
                "monthly_limit": _to_int(base.get("max_limit")),
                "join_way": str(base.get("join_way") or "").strip(),
                "special_condition": str(base.get("spcl_cnd") or "").strip(),
                "source_meta": base,
                "option": {
                    "save_trm": _to_int(option.get("save_trm")),
                    "intr_rate_type": str(option.get("intr_rate_type") or "")[:40],
                    "intr_rate_type_nm": str(option.get("intr_rate_type_nm") or "")[:80],
                    "intr_rate": _to_float(option.get("intr_rate")),
                    "intr_rate2": _to_float(option.get("intr_rate2")),
                    "rsrv_type": str(option.get("rsrv_type") or "")[:40],
                    "rsrv_type_nm": str(option.get("rsrv_type_nm") or "")[:80],
                    "source_meta": option,
                },
            }
        )
    return records


def _to_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0
