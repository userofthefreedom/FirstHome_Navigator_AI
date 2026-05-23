import tempfile
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.notice_docs.models import HousingUnitOption, NoticeDocument, PaymentSchedule
from apps.notice_docs.services import analyze_notice_document, analyze_notice_with_mock_data, parse_lh_document_candidates
from apps.notice_docs.services.pdf_parser import PdfPageText, download_remote_pdf, extract_pdf_table_text
from apps.notice_docs.services.retrieval import (
    build_document_chunks,
    candidate_chunks_for_notice_document,
    search_document_chunks,
)
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
        html_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "lh_detail_page.html"
        html = html_path.read_text(encoding="utf-8")

        candidates = parse_lh_document_candidates(html, "https://apply.lh.or.kr/lhapply/apply/detail")

        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0].file_id, "66680738")
        self.assertIn("입주자모집공고문.pdf", candidates[0].file_name)
        self.assertIn("/lhapply/lhFile.do?fileid=66680738", candidates[0].document_url)

    def test_rules_analysis_extracts_options_from_local_sample_pdf(self):
        pdf_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "public_sale_notice_611.pdf"
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
        analysis_summary = status_response.json()["analysis_summary"]
        self.assertEqual(latest_extraction["schema_version"], "rules-v1")
        self.assertIn(latest_extraction["source"], {"rules", "llm", "llm_cache"})
        self.assertIn(analysis_summary["stage"], {"verified", "needs_review"})
        self.assertFalse(analysis_summary["is_mock"])
        self.assertGreaterEqual(len(latest_extraction["evidence"]), 1)

    @patch("apps.notice_docs.services.analysis.download_remote_pdf")
    @patch("apps.notice_docs.services.analysis.discover_documents_for_notice")
    def test_rules_analysis_downloads_remote_pdf_document(self, mock_discover, mock_download):
        pdf_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "public_sale_notice_611.pdf"
        if not pdf_path.exists():
            self.skipTest("sample PDF is not available")

        document = NoticeDocument.objects.create(
            notice=self.notice,
            provider="LH",
            file_id="remote-pdf-1",
            file_name="notice.pdf",
            document_url="https://example.com/notice.pdf",
            source_url="https://example.com/detail",
        )
        mock_discover.return_value = [document]
        mock_download.return_value = pdf_path

        result = analyze_notice_document(self.notice)
        self.notice.refresh_from_db()
        document.refresh_from_db()

        mock_download.assert_called_once_with("https://example.com/notice.pdf", suggested_name="notice.pdf")
        self.assertEqual(self.notice.official_document_status, "analyzed")
        self.assertIsNotNone(document.fetched_at)
        self.assertEqual(result["extraction"].schema_version, "rules-v1")
        self.assertGreaterEqual(HousingUnitOption.objects.filter(notice=self.notice).count(), 1)

    @patch("apps.notice_docs.services.pdf_parser.requests.get")
    def test_download_remote_pdf_writes_and_reuses_cached_file(self, mock_get):
        response = Mock()
        response.headers = {"Content-Type": "application/pdf"}
        response.iter_content.return_value = [b"%PDF-1.4\n", b"sample"]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = download_remote_pdf(
                "https://example.com/lhFile.do?fileid=123",
                suggested_name="official.pdf",
                cache_dir=temp_dir,
            )
            second_path = download_remote_pdf(
                "https://example.com/lhFile.do?fileid=123",
                suggested_name="official.pdf",
                cache_dir=temp_dir,
            )

        self.assertIsNotNone(first_path)
        self.assertEqual(first_path, second_path)
        self.assertTrue(str(first_path).endswith("_official.pdf"))
        mock_get.assert_called_once()

    def test_extract_pdf_table_text_keeps_rows_for_rule_candidates(self):
        page = Mock()
        page.extract_tables.return_value = [
            [
                ["주택형", "층", "선택", "주택가격", "계약금", "중도금", "잔금", "융자금"],
                ["59A", "1층", "기본형", "320,000", "32,000", "192,000", "96,000", "0"],
            ]
        ]
        pdf_context = MagicMock()
        pdf_context.__enter__.return_value = SimpleNamespace(pages=[page])
        fake_pdfplumber = SimpleNamespace(open=Mock(return_value=pdf_context))

        with patch.dict("sys.modules", {"pdfplumber": fake_pdfplumber}):
            table_text = extract_pdf_table_text("sample.pdf")

        self.assertIn(1, table_text)
        self.assertIn("59A 1층 기본형 320,000 32,000 192,000 96,000 0", table_text[1])

    def test_document_retrieval_prioritizes_table_price_chunks(self):
        pages = [
            PdfPageText(page_no=1, text="모집공고 일반 안내입니다.\n\n청약 접수와 유의사항을 확인하세요."),
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 중도금 잔금 융자금\n"
                    "59A 1층 기본형 320,000 32,000 192,000 96,000 0"
                ),
            ),
            PdfPageText(page_no=8, text="무주택 세대구성원, 소득, 자산, 청약통장 가입기간을 확인합니다."),
        ]

        chunks = build_document_chunks(pages)
        ranked = search_document_chunks(pages, "계약금 중도금 잔금 주택가격", limit=2)
        prompt_chunks = candidate_chunks_for_notice_document(pages, limit_per_purpose=2)

        self.assertTrue(any(chunk.block_type == "table" for chunk in chunks))
        self.assertEqual(ranked[0].chunk.page_no, 4)
        self.assertEqual(ranked[0].chunk.block_type, "table")
        self.assertIn("59A", ranked[0].chunk.text)
        self.assertTrue(any("matched" in chunk and "주택가격" in chunk for chunk in prompt_chunks))
        self.assertTrue(any("무주택" in chunk for chunk in prompt_chunks))

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

        status_response = self.client.get(f"/api/notices/{self.notice.id}/documents/status")
        self.assertEqual(status_response.json()["analysis_summary"]["stage"], "mock")
        self.assertTrue(status_response.json()["analysis_summary"]["is_mock"])

    def test_batch_analysis_command_supports_dry_run(self):
        call_command("analyze_notice_documents", "--dry-run", "--limit=1")

    def test_batch_analysis_command_writes_pipeline_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = f"{temp_dir}/analysis_report.json"
            md_path = f"{temp_dir}/analysis_report.md"

            call_command(
                "analyze_notice_documents",
                "--dry-run",
                "--limit=1",
                f"--report-json={json_path}",
                f"--report-md={md_path}",
            )

            with open(json_path, encoding="utf-8") as report_file:
                report = json.load(report_file)
            with open(md_path, encoding="utf-8") as report_file:
                markdown = report_file.read()

        self.assertEqual(len(report["rows"]), 1)
        self.assertIn("pipeline_stage", report["rows"][0])
        self.assertIn("LH 분석 준비도 리포트", markdown)

    def test_representative_flow_command_completes_p0_scenario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = f"{temp_dir}/representative_flow.json"

            call_command("check_representative_flow", f"--report-json={json_path}")

            with open(json_path, encoding="utf-8") as report_file:
                report = json.load(report_file)

        self.assertTrue(report["ok"])
        self.assertEqual(report["notice_id"], 101)
        self.assertIn(report["analysis_stage"], {"verified", "needs_review"})
        self.assertGreater(report["option_id"], 0)
        self.assertEqual(
            [step["name"] for step in report["steps"]],
            [
                "profile_saved",
                "recommendation_loaded",
                "notice_detail_loaded",
                "official_analysis_ready",
                "unit_option_loaded",
                "option_funding_loaded",
                "ai_questions_answered",
                "favorite_saved",
            ],
        )

    def test_sample_pdf_expected_manifest_covers_current_regression_samples(self):
        expected_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "expected.json"
        data = json.loads(expected_path.read_text(encoding="utf-8"))
        samples = data["samples"]

        self.assertGreaterEqual(len(samples), 5)
        self.assertTrue(any(sample["kind"] == "include" for sample in samples))
        self.assertTrue(any(sample["kind"] == "exclude" for sample in samples))
        for sample in samples:
            self.assertTrue((settings.BASE_DIR / "fixtures" / "sample_pdfs" / sample["file_name"]).exists())
