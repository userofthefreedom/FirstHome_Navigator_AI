import json
import tempfile
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.ai_coach.models import AiChatLog, AiExtractionResult
from apps.ai_coach.services.ai_client import AiProviderUnavailable, chat_completion
from apps.notice_docs.models import EligibilityChecklist, ExtractionEvidence, HousingUnitOption, NoticeDocument, NoticeExtraction, PaymentSchedule
from apps.notices.models import HousingNotice


class AiExtractionResultTests(TestCase):
    def test_extraction_result_stores_structured_fields(self):
        result = AiExtractionResult.objects.create(
            source_type="notice",
            source_id=101,
            source_title="서울 청년 행복주택",
            source_url="https://example.com/notice/101",
            extraction_type="housing_notice",
            model_name="gpt-test",
            input_hash="a" * 64,
        )

        result.mark_succeeded(
            extracted_data={"deposit": 12000000, "monthly_rent": 180000},
            confidence={"deposit": 0.92, "monthly_rent": 0.87},
            missing_fields=["income_limit"],
            warnings=["income limit was not present in the source text"],
            raw_response={"id": "response-test"},
        )

        result.refresh_from_db()
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.extracted_data["deposit"], 12000000)
        self.assertEqual(result.confidence["deposit"], 0.92)
        self.assertEqual(result.missing_fields, ["income_limit"])
        self.assertEqual(result.error_message, "")

    def test_extraction_result_can_record_failure(self):
        result = AiExtractionResult.objects.create(
            source_type="policy",
            source_id=301,
            source_title="청년 월세 지원",
            extraction_type="youth_policy",
        )

        result.mark_failed("source document could not be parsed", raw_response={"status": 422})

        result.refresh_from_db()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_message, "source document could not be parsed")
        self.assertEqual(result.raw_response["status"], 422)

    def test_same_source_and_input_hash_is_unique(self):
        payload = {
            "source_type": "notice",
            "source_id": 101,
            "extraction_type": "housing_notice",
            "input_hash": "b" * 64,
        }
        AiExtractionResult.objects.create(**payload)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AiExtractionResult.objects.create(**payload)


@override_settings(
    AI_SETTINGS={
        "PROVIDER": "template",
        "MODEL": "test-model",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "OPENAI_CHAT_PATH": "/chat/completions",
        "LOCAL_LLM_ENDPOINT": "",
        "REQUEST_TIMEOUT": 30,
        "ENABLE_LLM_EXTRACTION": False,
        "ENABLE_LLM_CHAT": False,
    }
)
class AiCoachChatApiTests(TestCase):
    def test_chat_api_returns_template_fallback_response(self):
        response = self.client.post(
            "/api/ai/chat",
            {"notice_id": 101, "message": "부족액 알려줘", "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "template_fallback")
        self.assertEqual(payload["notice_id"], 101)
        self.assertIn("부족액", payload["reply"])
        self.assertGreaterEqual(len(payload["suggested_actions"]), 1)
        self.assertEqual(AiChatLog.objects.count(), 1)
        log = AiChatLog.objects.get()
        self.assertEqual(log.provider, "template")
        self.assertGreater(log.prompt_chars, 0)
        self.assertGreater(log.response_chars, 0)
        self.assertLessEqual(len(payload["reply"]), 420)
        self.assertLessEqual(len(payload["suggested_actions"]), 3)
        self.assertIn("공식", payload["reply"])

    def test_chat_context_refs_include_official_evidence_and_checklist(self):
        notice = HousingNotice.objects.create(
            title="Evidence public sale notice",
            provider="LH",
            region="Gyeonggi",
            district="Sample district",
            supply_type="public sale",
            housing_type="public sale housing",
            area="59m2",
            price=320000000,
            contract_rate=0.1,
            application_deadline="2026-06-01",
            winner_date="2026-06-10",
            contract_date="2026-07-01",
            move_in="2028-01",
            is_service_target=True,
            ownership_type="public_sale",
        )
        document = NoticeDocument.objects.create(notice=notice, provider="LH", file_name="notice.pdf")
        extraction = NoticeExtraction.objects.create(
            notice=notice,
            document=document,
            schema_version="rules-v1",
            status="valid",
            confidence=0.9,
            raw_json={"source": "rules"},
        )
        option = HousingUnitOption.objects.create(
            notice=notice,
            document=document,
            extraction=extraction,
            unit_type="59A",
            exclusive_area_m2=59.0,
            floor_group="basic",
            option_type="basic",
            base_price=320000000,
            source_page=12,
            source_text="59A supply price and payment row",
        )
        PaymentSchedule.objects.create(
            unit_option=option,
            label="down payment",
            amount=32000000,
            payment_type="down_payment",
            sequence=1,
            evidence_text="down payment evidence row",
        )
        EligibilityChecklist.objects.create(
            notice=notice,
            document=document,
            category="income",
            title="income check",
            condition_text="check income standard in official notice",
            evidence_text="income evidence sentence",
            confidence=0.8,
        )
        ExtractionEvidence.objects.create(
            extraction=extraction,
            field_path="unit_option.base_price",
            page_no=12,
            source_text="base price evidence sentence",
            confidence=0.8,
        )

        response = self.client.post(
            "/api/ai/chat",
            {"notice_id": notice.id, "option_id": option.id, "message": "공식 근거 알려줘", "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        ref_types = {ref["type"] for ref in response.json()["context_refs"]}
        self.assertIn("unit_option", ref_types)
        self.assertIn("payment_schedule", ref_types)
        self.assertIn("checklist", ref_types)
        self.assertIn("evidence", ref_types)
        self.assertEqual(AiChatLog.objects.latest("id").option_id, option.id)

    def test_template_provider_does_not_call_external_llm(self):
        with self.assertRaises(AiProviderUnavailable):
            chat_completion(messages=[{"role": "user", "content": "hello"}])

    def test_ai_chat_smoke_command_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = f"{temp_dir}/ai_chat_smoke.json"

            call_command("check_ai_chat_smoke", f"--report-json={json_path}")

            with open(json_path, encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertTrue(report["ok"])
        self.assertEqual(report["source"], "template_fallback")
        self.assertGreater(report["context_ref_count"], 0)
        self.assertGreater(report["log_id"], 0)

    @override_settings(
        AI_SETTINGS={
            "PROVIDER": "openai",
            "MODEL": "gpt-test",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_CHAT_PATH": "/chat/completions",
            "LOCAL_LLM_ENDPOINT": "",
            "REQUEST_TIMEOUT": 30,
            "ENABLE_LLM_EXTRACTION": False,
            "ENABLE_LLM_CHAT": True,
        }
    )
    @patch("apps.ai_coach.services.ai_client.requests.post")
    def test_llm_chat_logs_raw_response_and_usage_metrics(self, mock_post):
        raw_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"reply":"계약금 부족액을 먼저 확인하고 공식 공고문 확인이 필요합니다.",'
                            '"suggested_actions":["공식 공고문의 납부 일정을 확인하세요."],'
                            '"context_refs":[]}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
        }
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = raw_response
        mock_post.return_value = mock_response

        response = self.client.post(
            "/api/ai/chat",
            {"notice_id": 101, "message": "계약금 부족액 알려줘", "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "llm")
        log = AiChatLog.objects.get()
        self.assertEqual(log.provider, "openai")
        self.assertEqual(log.model_name, "gpt-test")
        self.assertEqual(log.raw_response["usage"]["prompt_tokens"], 1000)
        self.assertGreaterEqual(log.latency_ms, 0)
        self.assertGreater(log.estimated_cost_krw, 0)

    def test_chat_safety_filter_replaces_confirmed_expressions(self):
        response = self.client.post(
            "/api/ai/chat",
            {"notice_id": 101, "message": "신청 가능해?", "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"]
        self.assertNotIn("신청 가능합니다", reply)
        self.assertNotIn("당첨됩니다", reply)
        self.assertIn("공식", reply)
