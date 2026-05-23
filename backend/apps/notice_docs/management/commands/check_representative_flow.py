from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from apps.fixture_store import default_profile


REPRESENTATIVE_PROMPTS = [
    "이 공고에서 내가 가장 먼저 확인할 조건은?",
    "선택한 옵션의 계약금 부담은 어느 정도야?",
    "59A와 74A 중 지금 자금으로 더 현실적인 옵션은?",
    "공식 공고문에서 확인해야 할 문장은 어디야?",
    "이번 주에 해야 할 일을 3개로 정리해줘.",
]


class Command(BaseCommand):
    help = "Check the representative P0 user flow from fixture load to AI coach and favorites."

    def add_arguments(self, parser):
        parser.add_argument("--notice-id", type=int, default=101, help="Representative notice id to verify.")
        parser.add_argument(
            "--skip-reload",
            action="store_true",
            help="Use the current database instead of reloading fixture data with demo analysis.",
        )
        parser.add_argument("--report-json", help="Write the flow check result to a JSON file.")

    def handle(self, *args, **options):
        if not options["skip_reload"]:
            call_command("load_firsthome_fixture", "--with-demo-analysis", verbosity=0)

        notice_id = int(options["notice_id"])
        client = Client(HTTP_HOST="127.0.0.1")
        profile = default_profile()
        results: list[dict[str, Any]] = []

        self._step(results, "profile_saved", lambda: self._save_profile(client, profile))
        recommendation = self._step(results, "recommendation_loaded", lambda: self._load_recommendation(client, notice_id))
        selected_notice_id = int(recommendation["notice_id"])
        self._step(results, "notice_detail_loaded", lambda: self._load_notice_detail(client, selected_notice_id))
        status = self._step(results, "official_analysis_ready", lambda: self._load_document_status(client, selected_notice_id))
        option = self._step(results, "unit_option_loaded", lambda: self._load_unit_option(client, selected_notice_id, recommendation))
        self._step(results, "option_funding_loaded", lambda: self._load_option_funding(client, selected_notice_id, int(option["id"])))
        self._step(results, "ai_questions_answered", lambda: self._ask_ai_questions(client, selected_notice_id, int(option["id"]), profile))
        self._step(results, "favorite_saved", lambda: self._save_favorite(client, selected_notice_id))

        report = {
            "ok": True,
            "notice_id": selected_notice_id,
            "analysis_stage": status["analysis_summary"]["stage"],
            "option_id": option["id"],
            "steps": results,
        }
        self._write_report(report, options.get("report_json"))
        self.stdout.write(self.style.SUCCESS("Representative P0 flow check passed."))
        self.stdout.write(f"- notice #{selected_notice_id}")
        self.stdout.write(f"- option #{option['id']} {option.get('unit_type', '')}")
        self.stdout.write(f"- analysis stage: {status['analysis_summary']['stage']}")

    def _step(self, results: list[dict[str, Any]], name: str, fn):
        try:
            payload = fn()
        except Exception as exc:
            results.append({"name": name, "ok": False, "error": str(exc)})
            raise CommandError(f"{name} failed: {exc}") from exc
        results.append({"name": name, "ok": True})
        self.stdout.write(self.style.SUCCESS(f"[ok] {name}"))
        return payload

    def _save_profile(self, client: Client, profile: dict[str, Any]) -> dict[str, Any]:
        response = client.put("/api/profile", data=json.dumps(profile), content_type="application/json")
        payload = _json_response(response)
        _expect(response.status_code == 200, f"profile API returned {response.status_code}")
        _expect(payload.get("name") == profile.get("name"), "profile payload was not persisted")
        return payload

    def _load_recommendation(self, client: Client, notice_id: int) -> dict[str, Any]:
        response = client.get("/api/recommendations/housing")
        payload = _json_response(response)
        _expect(response.status_code == 200, f"recommendation API returned {response.status_code}")
        _expect(isinstance(payload, list) and payload, "recommendation list is empty")
        recommendation = next((item for item in payload if int(item["notice_id"]) == notice_id), payload[0])
        _expect(recommendation.get("is_service_target"), "selected recommendation is not a service target")
        return recommendation

    def _load_notice_detail(self, client: Client, notice_id: int) -> dict[str, Any]:
        response = client.get(f"/api/notices/{notice_id}")
        payload = _json_response(response)
        _expect(response.status_code == 200, f"notice detail API returned {response.status_code}")
        _expect(int(payload["id"]) == notice_id, "notice detail id mismatch")
        return payload

    def _load_document_status(self, client: Client, notice_id: int) -> dict[str, Any]:
        response = client.get(f"/api/notices/{notice_id}/documents/status")
        payload = _json_response(response)
        _expect(response.status_code == 200, f"document status API returned {response.status_code}")
        summary = payload.get("analysis_summary") or {}
        _expect(summary.get("stage") in {"verified", "needs_review"}, f"unexpected analysis stage: {summary.get('stage')}")
        _expect(int(payload.get("unit_option_count") or 0) > 0, "no analyzed unit options")
        return payload

    def _load_unit_option(self, client: Client, notice_id: int, recommendation: dict[str, Any]) -> dict[str, Any]:
        best_option_id = (recommendation.get("best_option") or {}).get("option_id")
        response = client.get(f"/api/notices/{notice_id}/unit-options")
        payload = _json_response(response)
        _expect(response.status_code == 200, f"unit option API returned {response.status_code}")
        _expect(isinstance(payload, list) and payload, "unit option list is empty")
        option = next((item for item in payload if item["id"] == best_option_id), payload[0])
        _expect(len(option.get("payment_schedules") or []) >= 3, "unit option has fewer than 3 payment schedules")
        return option

    def _load_option_funding(self, client: Client, notice_id: int, option_id: int) -> dict[str, Any]:
        response = client.get(f"/api/recommendations/funding/{notice_id}", {"option_id": option_id})
        payload = _json_response(response)
        _expect(response.status_code == 200, f"funding API returned {response.status_code}")
        _expect(payload.get("schedule_source") == "payment_schedule", "funding plan did not use payment schedule")
        _expect(int(payload.get("down_payment") or 0) > 0, "funding plan has no down payment")
        return payload

    def _ask_ai_questions(self, client: Client, notice_id: int, option_id: int, profile: dict[str, Any]) -> list[dict[str, Any]]:
        answers = []
        for prompt in REPRESENTATIVE_PROMPTS:
            response = client.post(
                "/api/ai/chat",
                data=json.dumps({"notice_id": notice_id, "option_id": option_id, "message": prompt, "profile": profile}),
                content_type="application/json",
            )
            payload = _json_response(response)
            _expect(response.status_code == 200, f"AI chat API returned {response.status_code}")
            _expect(payload.get("reply"), f"AI reply is empty for prompt: {prompt}")
            _expect("공식" in payload["reply"], f"AI reply does not include official-source caution: {prompt}")
            answers.append({"prompt": prompt, "source": payload.get("source"), "reply_length": len(payload["reply"])})
        return answers

    def _save_favorite(self, client: Client, notice_id: int) -> dict[str, Any]:
        headers = {"HTTP_X_FIRSTHOME_CLIENT_ID": "representative-flow-check"}
        response = client.post(
            "/api/favorites",
            data=json.dumps({"favorite_type": "notice", "object_id": notice_id}),
            content_type="application/json",
            **headers,
        )
        payload = _json_response(response)
        _expect(response.status_code == 201, f"favorite API returned {response.status_code}")
        _expect(payload.get("favorite_type") == "notice", "favorite type mismatch")

        list_response = client.get("/api/favorites", **headers)
        favorites = _json_response(list_response)
        _expect(list_response.status_code == 200, f"favorite list API returned {list_response.status_code}")
        _expect(any(item["favorite_type"] == "notice" and int(item["object_id"]) == notice_id for item in favorites), "favorite was not listed")
        return payload

    def _write_report(self, report: dict[str, Any], report_json: str | None) -> None:
        if not report_json:
            return
        path = Path(report_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote representative flow report: {path}"))


def _json_response(response) -> Any:
    try:
        return json.loads(response.content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"response is not JSON: {response.content[:120]!r}") from exc


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
