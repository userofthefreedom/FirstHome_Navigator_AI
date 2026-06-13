from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from apps.notice_docs.services import analyze_notice_document, notice_analysis_summary
from apps.notices.models import HousingNotice
from apps.rules.cache_service import clear_firsthome_cache


class Command(BaseCommand):
    help = "Run official-document discovery and PDF analysis for service-target notices."

    def add_arguments(self, parser):
        parser.add_argument("--notice-id", type=int, help="Analyze one notice only.")
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum notices to analyze. Defaults to 20 for dry-run and every pending notice for actual analysis.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-run notices that already have official analysis or mock fallback.",
        )
        parser.add_argument(
            "--include-failed",
            action="store_true",
            help="Retry notices whose previous analysis failed.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Show selected notices without running analysis.")
        parser.add_argument("--report-json", help="Write pipeline readiness rows to a JSON file.")
        parser.add_argument("--report-md", help="Write pipeline readiness rows to a Markdown table.")
        parser.add_argument("--include-excluded", action="store_true", help="Include notices outside the MVP service target.")
        parser.add_argument("--provider", help="Limit report/analysis to a provider such as LH.")
        parser.add_argument("--exclude-fixture", action="store_true", help="Skip fixture notices when building a readiness report.")

    def handle(self, *args, **options):
        queryset = HousingNotice.objects.all() if options["include_excluded"] else HousingNotice.objects.filter(is_service_target=True)
        queryset = queryset.order_by("application_deadline", "id")
        if options.get("provider"):
            queryset = queryset.filter(provider=options["provider"])
        if options["notice_id"]:
            queryset = queryset.filter(id=options["notice_id"])
        if not options["force"] and not options["include_excluded"]:
            statuses = ["not_requested", "pending"]
            if options["include_failed"]:
                statuses.append("failed")
            queryset = queryset.filter(official_document_status__in=statuses)

        notices = list(queryset)
        if options["exclude_fixture"]:
            notices = [
                notice
                for notice in notices
                if not isinstance(notice.source_meta, dict) or not notice.source_meta.get("fixture_id")
            ]
        limit = options["limit"] if options["limit"] is not None else (20 if options["dry_run"] else 0)
        if limit and not options["notice_id"]:
            notices = notices[:limit]
        rows: list[dict[str, Any]] = []
        if options["dry_run"]:
            self.stdout.write(f"Selected {len(notices)} notice(s) for analysis.")
            for notice in notices:
                summary = notice_analysis_summary(notice)
                rows.append(_report_row(notice, summary=summary, ran_analysis=False))
                self.stdout.write(f"- #{notice.id} {summary['label']} {notice.title}")
            self._write_reports(rows, options)
            return

        analyzed = 0
        failed = 0
        for notice in notices:
            if not notice.is_service_target:
                summary = notice_analysis_summary(notice)
                rows.append(_report_row(notice, summary=summary, ran_analysis=False))
                self.stdout.write(f"Skipping excluded #{notice.id} {notice.title}")
                continue
            self.stdout.write(f"Analyzing #{notice.id} {notice.title}")
            error_message = ""
            try:
                result = analyze_notice_document(notice)
            except Exception as exc:  # pragma: no cover - management command guardrail
                failed += 1
                error_message = str(exc)
                self.stderr.write(self.style.ERROR(f"  failed: {exc}"))
                notice.refresh_from_db()
                rows.append(_report_row(notice, error_message=error_message, ran_analysis=True))
                continue

            extraction = result.get("extraction")
            notice.refresh_from_db()
            summary = notice_analysis_summary(notice)
            analyzed += 1
            rows.append(_report_row(notice, summary=summary, error_message=error_message, ran_analysis=True))
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {summary['label']} | "
                    f"{getattr(extraction, 'schema_version', '')} | "
                    f"{len(result.get('unit_options', []))} option(s)"
                )
            )

        self._write_reports(rows, options)
        if analyzed:
            clear_firsthome_cache()
        self.stdout.write(self.style.SUCCESS(f"Finished: {analyzed} analyzed, {failed} failed."))

    def _write_reports(self, rows: list[dict[str, Any]], options: dict[str, Any]) -> None:
        if options.get("report_json"):
            path = Path(options["report_json"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"rows": rows, "summary": _report_summary(rows)}, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote JSON report: {path}"))
        if options.get("report_md"):
            path = Path(options["report_md"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_markdown_report(rows), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote Markdown report: {path}"))


def _report_row(
    notice: HousingNotice,
    *,
    summary: dict[str, Any] | None = None,
    error_message: str = "",
    ran_analysis: bool,
) -> dict[str, Any]:
    summary = summary or notice_analysis_summary(notice)
    latest_document = notice.documents.order_by("-updated_at", "-id").first()
    latest_extraction = notice.extractions.order_by("-created_at", "-id").first()
    latest_error = error_message or summary.get("latest_error", "")
    return {
        "notice_id": notice.id,
        "title": notice.title,
        "provider": notice.provider,
        "source_id": notice.source_id,
        "pipeline_stage": _pipeline_stage(summary, latest_error),
        "ran_analysis": ran_analysis,
        "official_document_status": notice.official_document_status,
        "document_status": getattr(latest_document, "status", ""),
        "document_count": summary.get("document_count", 0),
        "unit_option_count": summary.get("unit_option_count", 0),
        "schema_version": getattr(latest_extraction, "schema_version", ""),
        "extraction_status": getattr(latest_extraction, "status", ""),
        "analysis_stage": summary.get("stage", ""),
        "analysis_label": summary.get("label", ""),
        "latest_error": latest_error,
    }


def _pipeline_stage(summary: dict[str, Any], latest_error: str) -> str:
    if summary.get("stage") == "excluded":
        return "excluded_scope"
    if summary.get("unit_option_count", 0) > 0 and summary.get("stage") in {"verified", "needs_review"}:
        return "validation_passed"
    if summary.get("stage") == "mock":
        return "fallback_mock"
    if summary.get("document_count", 0) <= 0:
        return "discovery_failed"
    if latest_error:
        lowered = latest_error.lower()
        if "download" in lowered or "pdf" in lowered or "http" in lowered:
            return "pdf_download_failed"
        return "parser_or_rules_failed"
    if summary.get("document_status") == "pending":
        return "analysis_pending"
    return summary.get("stage", "unknown")


def _report_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        stage = str(row.get("pipeline_stage") or "unknown")
        result[stage] = result.get(stage, 0) + 1
    return result


def _markdown_report(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# LH 분석 준비도 리포트",
        "",
        "| 공고 ID | 단계 | 분석 상태 | 문서 | 옵션 | 스키마 | 오류 |",
        "|---:|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        error = str(row.get("latest_error") or "").replace("|", "/")[:80]
        lines.append(
            "| {notice_id} | {pipeline_stage} | {analysis_label} | {document_count} | "
            "{unit_option_count} | {schema_version} | {error} |".format(**{**row, "error": error})
        )
    lines.extend(["", "## 요약", ""])
    for stage, count in sorted(_report_summary(rows).items()):
        lines.append(f"- {stage}: {count}")
    return "\n".join(lines) + "\n"
