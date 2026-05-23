from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.notice_docs.services import analyze_notice_document, notice_analysis_summary
from apps.notices.models import HousingNotice


class Command(BaseCommand):
    help = "Run official-document discovery and PDF analysis for service-target notices."

    def add_arguments(self, parser):
        parser.add_argument("--notice-id", type=int, help="Analyze one notice only.")
        parser.add_argument("--limit", type=int, default=20, help="Maximum notices to analyze.")
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

    def handle(self, *args, **options):
        queryset = HousingNotice.objects.filter(is_service_target=True).order_by("application_deadline", "id")
        if options["notice_id"]:
            queryset = queryset.filter(id=options["notice_id"])
        if not options["force"]:
            statuses = ["not_requested", "pending"]
            if options["include_failed"]:
                statuses.append("failed")
            queryset = queryset.filter(official_document_status__in=statuses)
        if options["limit"] and not options["notice_id"]:
            queryset = queryset[: options["limit"]]

        notices = list(queryset)
        if options["dry_run"]:
            self.stdout.write(f"Selected {len(notices)} notice(s) for analysis.")
            for notice in notices:
                summary = notice_analysis_summary(notice)
                self.stdout.write(f"- #{notice.id} {summary['label']} {notice.title}")
            return

        analyzed = 0
        failed = 0
        for notice in notices:
            self.stdout.write(f"Analyzing #{notice.id} {notice.title}")
            try:
                result = analyze_notice_document(notice)
            except Exception as exc:  # pragma: no cover - management command guardrail
                failed += 1
                self.stderr.write(self.style.ERROR(f"  failed: {exc}"))
                continue

            extraction = result.get("extraction")
            summary = notice_analysis_summary(notice)
            analyzed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {summary['label']} | "
                    f"{getattr(extraction, 'schema_version', '')} | "
                    f"{len(result.get('unit_options', []))} option(s)"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Finished: {analyzed} analyzed, {failed} failed."))
