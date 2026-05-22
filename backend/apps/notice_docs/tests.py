from django.conf import settings
from django.test import TestCase, override_settings

from apps.notice_docs.models import HousingUnitOption, NoticeDocument, PaymentSchedule
from apps.notice_docs.services import analyze_notice_document, analyze_notice_with_mock_data, parse_lh_document_candidates
from apps.notices.models import HousingNotice


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
class NoticeDocsMockExtractionTests(TestCase):
    def setUp(self):
        self.notice = HousingNotice.objects.create(
            title="테스트 공공분양주택 입주자모집공고",
            provider="LH",
            region="서울",
            district="서울 테스트구",
            supply_type="공공분양",
            housing_type="공공분양주택",
            area="59m2",
            price=320000000,
            contract_rate=0.1,
            application_deadline="2026-06-01",
            winner_date="2026-06-10",
            contract_date="2026-07-01",
            move_in="2028-01",
            source_url="https://example.com/notice",
            is_service_target=True,
            ownership_type="public_sale",
        )

    def test_mock_analysis_creates_document_options_and_schedules(self):
        result = analyze_notice_with_mock_data(self.notice)
        self.notice.refresh_from_db()

        self.assertEqual(self.notice.official_document_status, "analyzed")
        self.assertEqual(result["document"].status, "analyzed")
        self.assertEqual(NoticeDocument.objects.count(), 1)
        self.assertGreaterEqual(HousingUnitOption.objects.filter(notice=self.notice).count(), 1)
        self.assertGreaterEqual(PaymentSchedule.objects.filter(unit_option__notice=self.notice).count(), 5)

    def test_lh_html_discovery_prefers_public_notice_pdf(self):
        html_path = settings.BASE_DIR.parent / "tmp_lh_page.html"
        html = html_path.read_text(encoding="utf-8")

        candidates = parse_lh_document_candidates(html, "https://apply.lh.or.kr/lhapply/apply/detail")

        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].file_id, "66680738")
        self.assertIn("입주자모집공고문.pdf", candidates[0].file_name)
        self.assertIn("/lhapply/lhFile.do?fileid=66680738", candidates[0].document_url)

    def test_rules_analysis_extracts_options_from_local_sample_pdf(self):
        pdf_path = settings.BASE_DIR.parent / "tmp_notice_611.pdf"
        if not pdf_path.exists():
            self.skipTest("sample PDF is not available")

        self.notice.source_url = str(pdf_path)
        self.notice.save(update_fields=["source_url"])

        result = analyze_notice_document(self.notice, pdf_path=pdf_path)
        self.notice.refresh_from_db()

        self.assertEqual(self.notice.official_document_status, "analyzed")
        self.assertEqual(result["extraction"].schema_version, "rules-v1")
        self.assertIn(result["extraction"].status, {"valid", "needs_review"})
        self.assertGreaterEqual(HousingUnitOption.objects.filter(notice=self.notice).count(), 1)
        option = HousingUnitOption.objects.filter(notice=self.notice).order_by("id").first()
        self.assertIsNotNone(option)
        assert option is not None
        self.assertGreater(option.base_price, 0)
        self.assertGreaterEqual(PaymentSchedule.objects.filter(unit_option=option).count(), 3)

        status_response = self.client.get(f"/api/notices/{self.notice.id}/documents/status")
        self.assertEqual(status_response.status_code, 200)
        latest_extraction = status_response.json()["latest_extraction"]
        self.assertEqual(latest_extraction["schema_version"], "rules-v1")
        self.assertIn(latest_extraction["source"], {"rules", "llm", "llm_cache"})

    def test_reanalysis_preserves_previous_result_when_pdf_is_unavailable(self):
        first_result = analyze_notice_with_mock_data(self.notice)
        first_option_ids = [option.id for option in first_result["unit_options"]]
        self.notice.source_url = ""
        self.notice.save(update_fields=["source_url"])

        result = analyze_notice_document(self.notice)
        self.notice.refresh_from_db()

        self.assertEqual(self.notice.official_document_status, "analyzed")
        self.assertEqual([option.id for option in result["unit_options"]], first_option_ids)
        self.assertGreaterEqual(HousingUnitOption.objects.filter(notice=self.notice).count(), 1)

    def test_analyze_api_returns_extraction_source_and_db_counts(self):
        self.notice.source_url = ""
        self.notice.save(update_fields=["source_url"])

        response = self.client.post(f"/api/notices/{self.notice.id}/documents/analyze")

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["extraction"]["schema_version"], "mock-v1")
        self.assertEqual(payload["extraction"]["source"], "mock")
        self.assertEqual(HousingUnitOption.objects.filter(notice=self.notice).count(), len(payload["unit_options"]))
        self.assertTrue(payload["unit_options"][0]["extraction_schema_version"])
