from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.ai_coach.models import AiChatLog, AiExtractionResult
from apps.ai_coach.services.ai_client import AiProviderUnavailable, chat_completion


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
        self.assertEqual(AiChatLog.objects.get().provider, "template")
        self.assertLessEqual(len(payload["reply"]), 420)
        self.assertLessEqual(len(payload["suggested_actions"]), 3)
        self.assertIn("공식", payload["reply"])

    def test_template_provider_does_not_call_external_llm(self):
        with self.assertRaises(AiProviderUnavailable):
            chat_completion(messages=[{"role": "user", "content": "hello"}])

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
