from __future__ import annotations

import json
from time import perf_counter
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings

from apps.notice_docs.services.analysis import analyze_notice_document
from apps.notice_docs.services.pdf_parser import parse_pdf_text
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload


class Command(BaseCommand):
    help = "Run regression checks for bundled sample PDF notices."

    def add_arguments(self, parser):
        parser.add_argument("--expected", default=str(settings.BASE_DIR / "fixtures" / "sample_pdfs" / "expected.json"))
        parser.add_argument(
            "--sample",
            action="append",
            default=[],
            help="Only run samples whose file_name matches this value. Can be passed multiple times.",
        )
        parser.add_argument("--kind", choices=["include", "exclude"], help="Only run samples of this regression kind.")
        parser.add_argument("--max-samples", type=int, default=0, help="Run at most this many selected samples.")
        parser.add_argument("--fail-fast", action="store_true", help="Stop at the first failing sample.")
        parser.add_argument("--report-json", help="Write sample regression result to a JSON file.")
        parser.add_argument("--report-md", help="Write a compact markdown summary to a file.")
        parser.add_argument("--snapshot-json", help="Write extracted option snapshots to a JSON file.")

    def handle(self, *args, **options):
        started_at = perf_counter()
        expected_path = Path(options["expected"])
        data = json.loads(expected_path.read_text(encoding="utf-8-sig"))
        rows: list[dict[str, Any]] = []

        selected_samples = _selected_samples(
            data.get("samples", []),
            set(options.get("sample") or []),
            kind=options.get("kind"),
            max_samples=int(options.get("max_samples") or 0),
        )
        for sample in selected_samples:
            row = self._check_sample(sample)
            rows.append(row)
            style = self.style.SUCCESS if row["ok"] else self.style.ERROR
            self.stdout.write(style(f"[{'ok' if row['ok'] else 'fail'}] {sample['file_name']} - {row['stage']}"))
            if options["fail_fast"] and not row["ok"]:
                break

        report = {
            "ok": bool(rows) and all(row["ok"] for row in rows),
            "summary": _summary(rows, duration_ms=round((perf_counter() - started_at) * 1000)),
            "rows": rows,
        }
        if options.get("report_json"):
            report_path = Path(options["report_json"])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote sample PDF regression report: {report_path}"))
        if options.get("report_md"):
            report_path = Path(options["report_md"])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(_markdown_report(report), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote sample PDF regression markdown: {report_path}"))
        if options.get("snapshot_json"):
            snapshot_path = Path(options["snapshot_json"])
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot = {"ok": report["ok"], "samples": [_snapshot_row(row) for row in rows]}
            snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote sample PDF regression snapshot: {snapshot_path}"))

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
            required_schedule_types = set(expected.get("required_schedule_types", []))
            required_option_types = set(expected.get("required_option_types", []))
            required_keywords = [str(keyword) for keyword in expected.get("required_keywords", [])]
            qualified_options = [
                option
                for option in options
                if _option_matches_expected(option, min_schedules, required_schedule_types)
            ]
            observed_option_types = {option.option_type for option in options}
            option_types_ok = not required_option_types or required_option_types.issubset(observed_option_types)
            missing_keywords = _missing_pdf_keywords(pdf_path, required_keywords)
            ok = len(qualified_options) >= min_options and option_types_ok and not missing_keywords
            return _row(
                sample,
                ok=ok,
                stage="extracted" if ok else "extraction_below_expected",
                option_count=len(options),
                qualified_option_count=len(qualified_options),
                required_schedule_types=sorted(required_schedule_types),
                observed_schedule_types=_observed_schedule_types(options),
                observed_option_types=sorted(observed_option_types),
                required_option_types=sorted(required_option_types),
                missing_keywords=missing_keywords,
                schema_version=getattr(result.get("extraction"), "schema_version", ""),
                extraction_status=getattr(result.get("extraction"), "status", ""),
                snapshot=_options_snapshot(options),
            )
        finally:
            notice.delete()


def _option_matches_expected(option: Any, min_schedules: int, required_schedule_types: set[str]) -> bool:
    schedules = list(option.payment_schedules.all())
    if len(schedules) < min_schedules:
        return False
    observed_schedule_types = {schedule.payment_type for schedule in schedules}
    return required_schedule_types.issubset(observed_schedule_types)


def _selected_samples(
    samples: list[dict[str, Any]],
    selected_names: set[str],
    *,
    kind: str | None = None,
    max_samples: int = 0,
) -> list[dict[str, Any]]:
    if not selected_names:
        selected = samples
    else:
        selected = [sample for sample in samples if sample.get("file_name") in selected_names]
    if kind:
        selected = [sample for sample in selected if sample.get("kind") == kind]
    if max_samples > 0:
        selected = selected[:max_samples]
    return selected


def _observed_schedule_types(options: list[Any]) -> list[str]:
    values: set[str] = set()
    for option in options:
        values.update(schedule.payment_type for schedule in option.payment_schedules.all())
    return sorted(values)


def _options_snapshot(options: list[Any]) -> dict[str, Any]:
    confidences = [float(getattr(option, "confidence", 0) or 0) for option in options]
    return {
        "option_count": len(options),
        "loan_option_count": sum(1 for option in options if int(getattr(option, "loan_amount", 0) or 0) > 0),
        "option_types": sorted({str(getattr(option, "option_type", "")) for option in options}),
        "schedule_types": _observed_schedule_types(options),
        "confidence": {
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0,
            "avg": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        },
        "options": [_option_snapshot(option) for option in options],
    }


def _option_snapshot(option: Any) -> dict[str, Any]:
    schedules = list(option.payment_schedules.all())
    return {
        "unit_type": option.unit_type,
        "floor_group": option.floor_group,
        "option_type": option.option_type,
        "base_price": option.base_price,
        "loan_amount": option.loan_amount,
        "confidence": float(option.confidence or 0),
        "schedule_count": len(schedules),
        "payment_types": [schedule.payment_type for schedule in schedules],
    }


def _snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "file_name": row["file_name"],
        "kind": row["kind"],
        "ownership_type": row.get("ownership_type", ""),
        "ok": row["ok"],
        "stage": row["stage"],
        "snapshot": row.get("snapshot", {}),
    }


def _missing_pdf_keywords(pdf_path: Path, required_keywords: list[str]) -> list[str]:
    if not required_keywords:
        return []
    document_text = "\n".join(page.text for page in parse_pdf_text(pdf_path, include_tables=False))
    return [keyword for keyword in required_keywords if keyword not in document_text]


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


def _summary(rows: list[dict[str, Any]], *, duration_ms: int) -> dict[str, Any]:
    return {
        "total": len(rows),
        "passed": sum(1 for row in rows if row["ok"]),
        "failed": sum(1 for row in rows if not row["ok"]),
        "included": sum(1 for row in rows if row.get("kind") == "include"),
        "excluded": sum(1 for row in rows if row.get("kind") == "exclude"),
        "duration_ms": duration_ms,
    }


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Sample PDF Regression",
        "",
        f"- ok: {report.get('ok')}",
        f"- total: {summary.get('total', 0)}",
        f"- passed: {summary.get('passed', 0)}",
        f"- failed: {summary.get('failed', 0)}",
        f"- duration_ms: {summary.get('duration_ms', 0)}",
        "",
        "| result | kind | file | stage |",
        "| --- | --- | --- | --- |",
    ]
    for row in report.get("rows", []):
        result = "ok" if row.get("ok") else "fail"
        lines.append(f"| {result} | {row.get('kind', '')} | {row.get('file_name', '')} | {row.get('stage', '')} |")
    lines.append("")
    return "\n".join(lines)
