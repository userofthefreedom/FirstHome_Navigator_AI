from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.ai_coach.models import AiChatLog
from apps.ai_coach.services.prompt_templates import coach_chat
from apps.fixture_store import default_profile


class Command(BaseCommand):
    help = "Run a smoke check for AI coach chat, with optional LLM enforcement."

    def add_arguments(self, parser):
        parser.add_argument("--notice-id", type=int, default=101, help="Notice id to ask about.")
        parser.add_argument("--option-id", type=int, help="Optional analyzed unit option id.")
        parser.add_argument(
            "--message",
            default="선택한 옵션의 계약금 부담과 공식 확인 포인트를 알려줘.",
            help="Smoke prompt to send to the AI coach.",
        )
        parser.add_argument(
            "--skip-reload",
            action="store_true",
            help="Use the current database instead of reloading fixture data with demo analysis.",
        )
        parser.add_argument(
            "--require-llm",
            action="store_true",
            help="Fail unless the response comes from the configured LLM provider.",
        )
        parser.add_argument("--report-json", help="Write the smoke result to a JSON file.")

    def handle(self, *args, **options):
        if not options["skip_reload"]:
            call_command("load_firsthome_fixture", "--with-demo-analysis", verbosity=0)

        notice_id = int(options["notice_id"])
        option_id = options.get("option_id")
        message = str(options["message"]).strip()
        if not message:
            raise CommandError("message must not be empty")

        before_log_id = AiChatLog.objects.order_by("-id").values_list("id", flat=True).first() or 0
        response = coach_chat(notice_id, message, default_profile(), option_id=option_id)
        if response is None:
            raise CommandError(f"AI chat returned no response for notice #{notice_id}")

        source = response.get("source", "")
        if options["require_llm"] and source != "llm":
            raise CommandError(f"LLM smoke required source=llm, got {source!r}")
        if not response.get("reply"):
            raise CommandError("AI chat reply is empty")
        if "공식" not in response["reply"]:
            raise CommandError("AI chat reply does not include official-source caution")

        latest_log = AiChatLog.objects.filter(id__gt=before_log_id).order_by("-id").first()
        report = {
            "ok": True,
            "notice_id": notice_id,
            "option_id": response.get("option_id"),
            "source": source,
            "reply_length": len(response["reply"]),
            "suggested_action_count": len(response.get("suggested_actions") or []),
            "context_ref_count": len(response.get("context_refs") or []),
            "log_id": latest_log.id if latest_log else None,
            "provider": latest_log.provider if latest_log else "",
            "latency_ms": latest_log.latency_ms if latest_log else 0,
            "estimated_cost_krw": latest_log.estimated_cost_krw if latest_log else 0,
        }
        self._write_report(report, options.get("report_json"))
        self.stdout.write(self.style.SUCCESS("AI chat smoke check passed."))
        self.stdout.write(f"- source: {source}")
        self.stdout.write(f"- context refs: {report['context_ref_count']}")
        self.stdout.write(f"- log id: {report['log_id']}")

    def _write_report(self, report: dict[str, Any], report_json: str | None) -> None:
        if not report_json:
            return
        path = Path(report_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote AI chat smoke report: {path}"))
