from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings

from apps.notice_docs.services.analysis import analyze_notice_document
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload


class Command(BaseCommand):
    help = "Run regression checks for bundled sample PDF notices."

    def add_arguments(self, parser):
        parser.add_argument("--expected", default=str(settings.BASE_DIR / "fixtures" / "sample_pdfs" / "expected.json"))
        parser.add_argument("--report-json", help="Write sample regression result to a JSON file.")

    def handle(self, *args, **options):
        expected_path = Path(options["expected"])
        data = json.loads(expected_path.read_text(encoding="utf-8"))
        rows: list[dict[str, Any]] = []

        for sample in data.get("samples", []):
            row = self._check_sample(sample)
            rows.append(row)
            style = self.style.SUCCESS if row["ok"] else self.style.ERROR
            self.stdout.write(style(f"[{'ok' if row['ok'] else 'fail'}] {sample['file_name']} - {row['stage']}"))

        report = {"ok": all(row["ok"] for row in rows), "rows": rows}
        if options.get("report_json"):
            report_path = Path(options["report_json"])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote sample PDF regression report: {report_path}"))

        if not report["ok"]:
            failed = ", ".join(row["file_name"] for row in rows if not row["ok"])
            raise CommandError(f"Sample PDF regression failed: {failed}")

    def _check_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        pdf_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / sample["file_name"]
        if not pdf_path.exists():
            return _row(sample, ok=False, stage="missing_file", error="sample file does not exist")

        if sample["kind"] == "exclude":
            return self._check_excluded_sample(sample)
        return self._check_included_sample(sample, pdf_path)

    def _check_excluded_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "title": sample["file_name"],
            "provider": "LH",
            "supply_type": sample.get("case_type", ""),
            "housing_type": sample.get("case_type", ""),
            "district": sample["file_name"],
            "tags": sample.get("expected", {}).get("exclude_keywords", []),
        }
        classification = classify_notice_payload(payload)
        ok = classification.ownership_type == "excluded" and not classification.is_service_target
        return _row(
            sample,
            ok=ok,
            stage="excluded_classified" if ok else "excluded_classification_failed",
            ownership_type=classification.ownership_type,
            exclude_reason=classification.exclude_reason,
        )

    def _check_included_sample(self, sample: dict[str, Any], pdf_path: Path) -> dict[str, Any]:
        notice = HousingNotice.objects.create(
            source_id=f"sample:{sample['file_name']}"[:80],
            title=_title_for_sample(sample),
            provider="LH",
            region="경기 남부",
            district="샘플 공고",
            supply_type="공공분양",
            housing_type="공공분양주택",
            area="59m2",
            price=320000000,
            contract_rate=0.1,
            application_deadline=date(2026, 6, 30),
            winner_date=date(2026, 7, 15),
            contract_date=date(2026, 7, 30),
            move_in="2028-01",
            source_url=str(pdf_path),
            tags=["LH", "공공분양"],
            ownership_type=sample.get("ownership_type", "public_sale"),
            is_service_target=True,
        )
        try:
            ai_settings = getattr(settings, "AI_SETTINGS", {}).copy()
            ai_settings["ENABLE_LLM_EXTRACTION"] = False
            with override_settings(AI_SETTINGS=ai_settings):
                result = analyze_notice_document(notice, pdf_path=pdf_path)
            options = result.get("unit_options", [])
            expected = sample.get("expected", {})
            min_options = int(expected.get("min_unit_options", 1))
            min_schedules = int(expected.get("min_payment_schedules_per_option", 1))
            qualified_options = [option for option in options if option.payment_schedules.count() >= min_schedules]
            ok = len(qualified_options) >= min_options
            return _row(
                sample,
                ok=ok,
                stage="extracted" if ok else "extraction_below_expected",
                option_count=len(options),
                qualified_option_count=len(qualified_options),
                schema_version=getattr(result.get("extraction"), "schema_version", ""),
                extraction_status=getattr(result.get("extraction"), "status", ""),
            )
        finally:
            notice.delete()


def _title_for_sample(sample: dict[str, Any]) -> str:
    ownership_type = sample.get("ownership_type")
    if ownership_type == "newlywed_public_sale":
        return "신혼희망타운 공공분양 입주자모집공고"
    if ownership_type == "private_participation_public_sale":
        return "민간참여 공공분양 입주자모집공고"
    return "공공분양주택 입주자모집공고"


def _row(sample: dict[str, Any], *, ok: bool, stage: str, **extra: Any) -> dict[str, Any]:
    return {
        "file_name": sample["file_name"],
        "kind": sample["kind"],
        "ownership_type": sample.get("ownership_type", ""),
        "ok": ok,
        "stage": stage,
        **extra,
    }
