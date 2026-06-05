import json
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from apps.ai_coach.models import AiChatLog, AiCoachPlan, AiExtractionResult
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

    def test_chat_api_answers_service_usage_with_page_context(self):
        response = self.client.post(
            "/api/ai/chat",
            {
                "notice_id": 101,
                "message": "이 화면은 어떻게 쓰면 돼?",
                "profile": {"asset": 8000000},
                "page_context": {
                    "path": "/recommendations",
                    "page_type": "recommendations",
                    "is_authenticated": False,
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "template_fallback")
        self.assertEqual(payload["page_context"]["page_type"], "recommendations")
        self.assertIn("추천 청약", payload["reply"])
        self.assertTrue(any("공고" in action or "자금" in action for action in payload["suggested_actions"]))

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
            raw_json={"source": "rules", "required_documents": ["주민등록표등본"]},
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
        self.assertIn("required_document", ref_types)
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

    def test_ai_chat_smoke_command_runs_safety_suite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = f"{temp_dir}/ai_chat_suite.json"

            call_command("check_ai_chat_smoke", "--suite", f"--report-json={json_path}")

            with open(json_path, encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertTrue(report["ok"])
        self.assertGreaterEqual(len(report["rows"]), 5)
        self.assertTrue(all(row["ok"] for row in report["rows"]))
        self.assertFalse(any(row["blocked_phrases"] for row in report["rows"]))

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
    def test_llm_coach_summary_returns_action_plan(self, mock_post):
        user = User.objects.create_user(username="coach-user", password="pw")
        self.client.force_login(user)
        raw_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "계약금 부족액과 접수 마감을 먼저 확인하고 공식 공고문 확인이 필요합니다.",
                                "todo_this_week": [
                                    "계약금 부족액을 자금 로드맵에서 확인하세요.",
                                    "무주택과 소득 기준을 공식 공고문에서 확인하세요.",
                                    "관심 후보를 저장하고 비교하세요.",
                                ],
                                "official_checklist": [
                                    "무주택 기준",
                                    "소득과 자산 기준",
                                    "납부 일정",
                                ],
                                "deep_review_items": [
                                    {
                                        "title": "지역우선 기준",
                                        "body": "거주기간과 지역우선 배정 기준을 확인하세요.",
                                        "why_it_matters": "거주기간에 따라 배정 물량이 달라질 수 있습니다.",
                                    },
                                    {
                                        "title": "특별공급 세부 조건",
                                        "body": "신혼부부나 생애최초 조건을 공식 공고문에서 대조하세요.",
                                        "why_it_matters": "공급유형별 자격이 서로 다를 수 있습니다.",
                                    },
                                ],
                                "decision_points": [
                                    {
                                        "title": "우선 후보 고정",
                                        "body": "대표 주택형을 기준으로 계약금 부담을 먼저 확인하세요.",
                                        "cta": "옵션 자금 보기",
                                    },
                                    {
                                        "title": "부족액 준비",
                                        "body": "월 준비 목표를 보유 현금과 함께 다시 계산하세요.",
                                        "cta": "조건 수정",
                                    },
                                    {
                                        "title": "공식 확인",
                                        "body": "자격과 납부 일정은 공식 공고문을 우선하세요.",
                                        "cta": "공식 근거 보기",
                                    },
                                ],
                                "warning": "추천 결과는 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다. 공식 공고문 확인이 필요합니다.",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 600},
        }
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = raw_response
        mock_post.return_value = mock_response

        response = self.client.post(
            "/api/ai/coach-summary",
            {"notice_id": 101, "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "llm")
        self.assertEqual(len(payload["decision_points"]), 3)
        self.assertGreaterEqual(len(payload["deep_review_items"]), 2)
        self.assertGreaterEqual(len(payload["todo_this_week"]), 3)
        log = AiChatLog.objects.get(question="AI Coach summary")
        self.assertEqual(log.provider, "openai")
        self.assertEqual(log.model_name, "gpt-test")
        self.assertGreater(log.estimated_cost_krw, 0)
        self.assertEqual(AiCoachPlan.objects.count(), 1)

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
    def test_anonymous_coach_summary_returns_sample_without_llm_call(self, mock_post):
        response = self.client.post(
            "/api/ai/coach-summary",
            {"notice_id": 101, "profile": {"asset": 8000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "login_required_sample")
        self.assertTrue(payload["requires_login"])
        self.assertIn("로그인", payload["login_message"])
        mock_post.assert_not_called()
        self.assertEqual(AiCoachPlan.objects.count(), 0)

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
    def test_logged_in_coach_summary_reuses_cached_llm_plan_for_same_option(self, mock_post):
        user = User.objects.create_user(username="cache-user", password="pw")
        self.client.force_login(user)
        raw_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "선택 옵션 기준 계약금 부족액과 공식 서류를 함께 확인하세요.",
                                "todo_this_week": [
                                    "선택 옵션의 계약금 부족액을 저축 계획으로 바꾸세요.",
                                    "공식 제출서류 후보를 우선순위로 정리하세요.",
                                    "발코니 확장과 추가 선택품목의 유상 여부를 확인하세요.",
                                ],
                                "official_checklist": [
                                    "제출서류 목록",
                                    "발코니/추가 선택품목",
                                    "납부 일정",
                                ],
                                "deep_review_items": [
                                    {
                                        "title": "공고문 세부 조건",
                                        "body": "지역우선과 특별공급 조건을 별도로 확인하세요.",
                                        "why_it_matters": "룰 화면에서 완전히 판단하기 어려운 조건입니다.",
                                    }
                                ],
                                "decision_points": [
                                    {"title": "자금 계획", "body": "부족액을 월 목표로 나누어 준비하세요.", "cta": "자금 보기"},
                                    {"title": "서류 준비", "body": "공식 제출서류를 먼저 확인하세요.", "cta": "공식 근거"},
                                    {"title": "선택품목", "body": "추가 선택품목 비용을 별도로 확인하세요.", "cta": "공고문 보기"},
                                ],
                                "warning": "금액과 일정은 참고용이며 공식 공고문 확인이 필요합니다.",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 600},
        }
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = raw_response
        mock_post.return_value = mock_response

        request_body = {"notice_id": 101, "profile": {"asset": 8000000}}
        first = self.client.post("/api/ai/coach-summary", request_body, content_type="application/json")
        second = self.client.post("/api/ai/coach-summary", request_body, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["source"], "llm")
        self.assertEqual(second.json()["source"], "cached_llm")
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(AiCoachPlan.objects.count(), 1)

    def test_coach_summary_accepts_option_id_for_selected_option_context(self):
        notice = HousingNotice.objects.create(
            title="Option specific public sale notice",
            provider="LH",
            region="경기 남부",
            district="Sample district",
            supply_type="공공분양",
            housing_type="공공분양주택",
            area="84m2",
            price=690000000,
            contract_rate=0.1,
            application_deadline="2026-06-12",
            winner_date="2026-06-20",
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
            unit_type="84A",
            exclusive_area_m2=84.0,
            floor_group="1층",
            option_type="general_supply",
            base_price=691900000,
        )
        PaymentSchedule.objects.create(
            unit_option=option,
            label="계약금",
            amount=56920000,
            payment_type="down_payment",
            sequence=1,
        )

        response = self.client.post(
            "/api/ai/coach-summary",
            {"notice_id": notice.id, "option_id": option.id, "profile": {"asset": 12000000}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["option_id"], option.id)
        self.assertIn("부족", payload["summary"])

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
