import tempfile
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.ai_coach.models import AiExtractionResult
from apps.ai_coach.services.ai_client import AiClientError
from apps.notice_docs.models import HousingUnitOption, NoticeDocument, NoticeExtraction, PaymentSchedule
from apps.notice_docs.services import analyze_notice_document, analyze_notice_with_mock_data, parse_lh_document_candidates
from apps.notice_docs.services.extractors import (
    extract_checklist_items,
    extract_required_documents_from_pages,
    extract_unit_options_from_pages,
)
from apps.notice_docs.services.llm_extractors import _checklists_from_payload, _option_from_payload, extract_notice_document_with_llm
from apps.notice_docs.services.pdf_parser import PdfPageText, clear_pdf_text_cache, download_remote_pdf, extract_pdf_table_text, parse_pdf_text
from apps.notice_docs.services.retrieval import (
    build_document_chunks,
    candidate_chunks_for_notice_document,
    search_document_chunks,
)
from apps.notice_docs.services.schemas import NOTICE_DOCUMENT_EXTRACTION_SCHEMA
from apps.notices.models import HousingNotice


@override_settings(
    AI_SETTINGS={
        "PROVIDER": "template",
        "MODEL": "test-model",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "OPENAI_CHAT_PATH": "/chat/completions",
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

    def test_lh_html_discovery_ranks_notice_pdf_above_auxiliary_files(self):
        html = """
        <a href="javascript:fileDownLoad('1001');">단지 팸플릿.pdf</a>
        <a href="javascript:fileDownLoad('1002');">동호배치도.pdf</a>
        <a href="javascript:fileDownLoad('1003');">공급신청서 서식.hwp</a>
        <a href="javascript:fileDownLoad('1004');">시흥하중 A1블록 신혼희망타운 입주자모집공고문.pdf</a>
        """

        candidates = parse_lh_document_candidates(html, "https://apply.lh.or.kr/lhapply/apply/detail")

        self.assertEqual(candidates[0].file_id, "1004")
        self.assertIn("입주자모집공고문", candidates[0].file_name)

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

    @override_settings(PDF_TEXT_CACHE_ENABLED=True)
    def test_parse_pdf_text_reuses_in_process_text_cache_only(self):
        pdf_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "public_sale_notice_611.pdf"
        if not pdf_path.exists():
            self.skipTest("sample PDF is not available")

        clear_pdf_text_cache()
        first_pages = parse_pdf_text(pdf_path, max_pages=1, include_tables=False)
        with patch("pypdf.PdfReader") as mock_reader:
            second_pages = parse_pdf_text(pdf_path, max_pages=1, include_tables=False)
        cache_dir = settings.BASE_DIR / ".cache" / "pdf_text"

        self.assertEqual(first_pages, second_pages)
        mock_reader.assert_not_called()
        self.assertFalse(cache_dir.exists())

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

    def test_document_retrieval_includes_required_document_chunks(self):
        pages = [
            PdfPageText(page_no=3, text="주택형 공급금액 안내\n[table 1]\n주택형 주택가격 계약금 중도금 잔금\n59A 320,000 32,000 192,000 96,000"),
            PdfPageText(
                page_no=18,
                text=(
                    "당첨자 제출서류 및 구비서류\n"
                    "주민등록표등본, 가족관계증명서, 소득금액증명, 건강보험자격득실확인서, 개인정보 제공 동의서"
                ),
            ),
        ]

        ranked = search_document_chunks(pages, "제출서류 주민등록 가족관계 소득금액", limit=2)
        prompt_chunks = candidate_chunks_for_notice_document(pages, limit_per_purpose=2)

        self.assertEqual(ranked[0].chunk.page_no, 18)
        self.assertIn("주민등록표등본", ranked[0].chunk.text)
        self.assertTrue(any("제출서류" in chunk and "주민등록표등본" in chunk for chunk in prompt_chunks))

    def test_required_document_extractor_collects_submission_documents(self):
        pages = [
            PdfPageText(page_no=2, text="공고 개요 및 신청 유의사항"),
            PdfPageText(
                page_no=29,
                text=(
                    "당첨자 제출서류 안내\n"
                    "당첨자 본인 신분증 주민등록표등본 주민등록표초본 개인정보 수집·이용 및 제3자 제공동의서\n"
                    "가족관계증명서 혼인관계증명서 출입국에 관한 사실증명 재직증명서 임신증명서류 또는 출생증명서"
                ),
            ),
            PdfPageText(
                page_no=32,
                text=(
                    "계약 시 구비서류\n"
                    "계약금 입금 확인서류 주택취득 자금 조달 및 입주계획서 위임장 인감증명서 본인서명사실확인서"
                ),
            ),
        ]

        documents = extract_required_documents_from_pages(pages)

        self.assertGreaterEqual(len(documents), 10)
        self.assertIn("당첨자 본인 신분증", documents)
        self.assertIn("주민등록표등본", documents)
        self.assertIn("주민등록표초본", documents)
        self.assertIn("개인정보 수집·이용 및 제3자 제공 동의서", documents)
        self.assertIn("계약금 입금 확인서류", documents)

    @patch("apps.notice_docs.services.analysis.parse_pdf_text")
    @patch("apps.notice_docs.services.analysis.discover_documents_for_notice")
    def test_analysis_updates_notice_required_documents_from_pdf(self, mock_discover, mock_parse_pdf_text):
        document = NoticeDocument.objects.create(
            notice=self.notice,
            provider="LH",
            file_name="notice.pdf",
            document_url=str(settings.BASE_DIR / "fixtures" / "sample_pdfs" / "public_sale_notice_611.pdf"),
            source_url="https://example.com/detail",
            status="discovered",
        )
        mock_discover.return_value = [document]
        mock_parse_pdf_text.return_value = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 중도금 잔금 융자금\n"
                    "59A 1층 기본형 320,000 32,000 192,000 96,000 0"
                ),
            ),
            PdfPageText(
                page_no=29,
                text=(
                    "당첨자 제출서류 주민등록표등본 주민등록표초본 개인정보 수집·이용 및 제3자 제공동의서 "
                    "가족관계증명서 혼인관계증명서 출입국에 관한 사실증명"
                ),
            ),
        ]

        analyze_notice_document(self.notice)
        self.notice.refresh_from_db()

        self.assertIn("주민등록표초본", self.notice.required_documents)
        self.assertIn("개인정보 수집·이용 및 제3자 제공 동의서", self.notice.required_documents)
        self.assertIn("가족관계증명서", self.notice.required_documents)

    def test_checklist_extractor_prefers_detail_pages_over_intro_notice(self):
        pages = [
            PdfPageText(
                page_no=1,
                text="신청자격 무주택 소득 자산 거주 입주자저축을 사전에 확인하시기 바랍니다.",
            ),
            PdfPageText(
                page_no=11,
                text=(
                    "2. 무주택세대구성원 및 주택소유여부 판정 기준 "
                    "무주택세대구성원 여부는 주택공급에 관한 규칙에 따라 판단합니다. "
                    "지역우선공급 해당 주택건설지역 거주자 및 기타지역 거주자 기준을 적용합니다."
                ),
            ),
            PdfPageText(
                page_no=15,
                text="소득기준 소득기준 소득기준 자산기준 총자산 기준을 확인합니다.",
            ),
            PdfPageText(
                page_no=23,
                text="입주자저축 청약통장 가입기간 및 납입인정 횟수를 확인합니다.",
            ),
        ]

        by_title = {item["title"]: item for item in extract_checklist_items(pages)}

        self.assertEqual(by_title["무주택 기준 확인"]["page_no"], 11)
        self.assertEqual(by_title["지역 우선공급 확인"]["page_no"], 11)
        self.assertEqual(by_title["소득·자산 기준 확인"]["page_no"], 15)
        self.assertEqual(by_title["청약통장 요건 확인"]["page_no"], 23)
        self.assertEqual(by_title["무주택 기준 확인"]["condition_text"], "")
        self.assertGreater(by_title["무주택 기준 확인"]["confidence"], 0.5)

    def test_llm_option_backfills_area_from_lh_supply_summary(self):
        self.notice.source_meta = {
            "supply_summary": {
                "unit_options": [
                    {
                        "unit_type": "74A",
                        "raw_unit_type": "74.9500A",
                        "exclusive_area_m2": 74.95,
                    }
                ]
            }
        }

        option = _option_from_payload(
            {
                "unit_type": "74.9500A",
                "exclusive_area_m2": 0,
                "floor_group": "1층",
                "option_type": "basic",
                "base_price": 518230000,
                "loan_amount": 0,
                "balcony_extension_price": 0,
                "confidence": 0.7,
                "source_page": 5,
                "source_text": "74.9500A 1층 기본형 518,230",
                "payment_schedules": [],
                "evidence": [],
            },
            notice=self.notice,
        )

        self.assertEqual(option.exclusive_area_m2, 74.95)

    def test_llm_schema_matches_current_option_group_contract(self):
        option_schema = NOTICE_DOCUMENT_EXTRACTION_SCHEMA["schema"]["properties"]["unit_options"]["items"]
        option_types = set(option_schema["properties"]["option_type"]["enum"])
        payment_types = set(
            option_schema["properties"]["payment_schedules"]["items"]["properties"]["payment_type"]["enum"]
        )
        checklist_schema = NOTICE_DOCUMENT_EXTRACTION_SCHEMA["schema"]["properties"]["eligibility_checklists"]["items"]
        root_required = set(NOTICE_DOCUMENT_EXTRACTION_SCHEMA["schema"]["required"])

        self.assertIn("general_supply", option_types)
        self.assertIn("pre_subscription", option_types)
        self.assertNotIn("loan", payment_types)
        self.assertIn("page_no", checklist_schema["properties"])
        self.assertIn("page_no", checklist_schema["required"])
        self.assertIn("required_documents", root_required)

    def test_llm_payload_normalizes_option_type_and_checklist_page(self):
        option = _option_from_payload(
            {
                "unit_type": "59A",
                "exclusive_area_m2": 59,
                "floor_group": "1층",
                "option_type": "general",
                "base_price": 500000000,
                "loan_amount": 55000000,
                "balcony_extension_price": 0,
                "confidence": 0.7,
                "source_page": 5,
                "source_text": "본청약 계약금(10%)",
                "payment_schedules": [
                    {
                        "label": "계약금",
                        "due_date": "",
                        "amount": 50000000,
                        "payment_type": "down_payment",
                        "sequence": 1,
                        "evidence_text": "계약금",
                    },
                    {
                        "label": "융자금",
                        "due_date": "",
                        "amount": 55000000,
                        "payment_type": "loan",
                        "sequence": 2,
                        "evidence_text": "융자금",
                    },
                ],
                "evidence": [],
            },
            notice=self.notice,
        )
        checklists = _checklists_from_payload(
            {
                "eligibility_checklists": [
                    {
                        "category": "income",
                        "title": "소득 기준 확인",
                        "condition_text": "",
                        "evidence_text": "소득 및 자산 기준",
                        "page_no": 15,
                        "confidence": 0.8,
                    }
                ]
            }
        )

        self.assertEqual(option.option_type, "general_supply")
        self.assertEqual(option.loan_amount, 55000000)
        self.assertEqual([schedule.payment_type for schedule in option.payment_schedules], ["down_payment"])
        self.assertEqual(checklists[0]["page_no"], 15)

    @patch("apps.notice_docs.services.llm_extractors.chat_completion")
    @patch("apps.notice_docs.services.llm_extractors.llm_enabled")
    def test_llm_extraction_falls_back_to_latest_successful_cache(self, mock_llm_enabled, mock_chat_completion):
        mock_llm_enabled.return_value = True
        mock_chat_completion.side_effect = AiClientError("temporary model outage")
        AiExtractionResult.objects.create(
            source_type="document",
            source_id=123,
            extraction_type="housing_notice",
            input_hash="previous-hash",
            status="succeeded",
            model_name="cached-model",
            prompt_version="notice-doc-llm-v2",
            extracted_data={
                "unit_options": [
                    {
                        "unit_type": "59A",
                        "exclusive_area_m2": 59,
                        "floor_group": "1층",
                        "option_type": "general_supply",
                        "base_price": 500000000,
                        "loan_amount": 55000000,
                        "balcony_extension_price": 0,
                        "confidence": 0.82,
                        "source_page": 5,
                        "source_text": "59A 1층 본청약",
                        "payment_schedules": [],
                        "evidence": [],
                    }
                ],
                "eligibility_checklists": [],
                "required_documents": ["주민등록표등본"],
                "warnings": [],
            },
        )

        options, checklists, meta = extract_notice_document_with_llm(
            notice=self.notice,
            document_id=123,
            pages=[PdfPageText(page_no=5, text="주택가격 계약금 중도금 잔금 59A")],
        )

        self.assertEqual(meta["source"], "llm_stale_cache")
        self.assertEqual(options[0].option_type, "general_supply")
        self.assertEqual(options[0].loan_amount, 55000000)
        self.assertEqual(meta["required_documents"], ["주민등록표등본"])
        self.assertEqual(checklists, [])

    def test_rules_extractor_normalizes_unit_type_and_skips_invalid_area(self):
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 중도금 잔금 융자금\n"
                    "059A 1층 기본형 320,000 32,000 192,000 96,000 0\n"
                    "200A 1층 잘못된행 320,000 32,000 192,000 96,000 0"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual([option.unit_type for option in options], ["59A"])
        self.assertEqual(options[0].exclusive_area_m2, 59.0)

    def test_rules_extractor_reads_area_prefix_rows_without_treating_area_code_as_unit(self):
        pages = [
            PdfPageText(
                page_no=6,
                text=(
                    "공급금액 및 납부일정\n"
                    "주택가격 계약금 중도금 잔금 융자금\n"
                    "B1블록 (1단지) 074.9400A 74A 101동(3호) 1층 3 "
                    "495,516,000 24,775,000 148,654,000 247,087,000 75,000,000\n"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].unit_type, "74A")
        self.assertEqual(options[0].exclusive_area_m2, 74.0)
        self.assertEqual(options[0].floor_group, "B1블록 1층")
        self.assertEqual(options[0].base_price, 495516000)
        self.assertEqual(options[0].loan_amount, 75000000)
        self.assertEqual(
            [schedule.payment_type for schedule in options[0].payment_schedules],
            ["down_payment", "middle_payment", "final_payment"],
        )

    def test_rules_extractor_normalizes_broken_floor_glyphs(self):
        pages = [
            PdfPageText(
                page_no=5,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 주택가격 계약금 중도금 잔금 융자금\n"
                    "51A 1Уў 555,310,000 27,765,500 111,062,000 361,482,500 55,000,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].floor_group, "1층")
        self.assertEqual(options[0].loan_amount, 55000000)

    def test_rules_extractor_allows_no_middle_payment_schedule(self):
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 잔금\n"
                    "59A 전체 기본형 320,000 32,000 288,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        self.assertEqual(
            [schedule.payment_type for schedule in options[0].payment_schedules],
            ["down_payment", "final_payment"],
        )
        self.assertEqual(options[0].loan_amount, 0)

    def test_rules_extractor_allows_no_middle_payment_with_loan_column(self):
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 잔금 융자금\n"
                    "59A 전체 기본형 320,000 32,000 248,000 40,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        self.assertEqual(
            [schedule.payment_type for schedule in options[0].payment_schedules],
            ["down_payment", "final_payment"],
        )
        self.assertEqual(options[0].loan_amount, 40000000)

    def test_rules_extractor_allows_single_middle_payment_schedule(self):
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 중도금 잔금\n"
                    "59A 전체 기본형 320,000 32,000 192,000 96,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        middle_schedules = [schedule for schedule in options[0].payment_schedules if schedule.payment_type == "middle_payment"]
        self.assertEqual(len(middle_schedules), 1)
        self.assertEqual(middle_schedules[0].label, "중도금 1차")
        self.assertEqual(options[0].loan_amount, 0)

    def test_rules_extractor_allows_many_middle_payment_schedules(self):
        dates = " ".join(f"2027.{month:02d}.01" for month in range(1, 11))
        middle_amounts = " ".join(["35,000"] * 10)
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 납부일정\n"
                    f"중도금 납부일 {dates}\n"
                    "[table 1]\n"
                    "주택형 층 선택 주택가격 계약금 중도금 잔금\n"
                    f"59A 전체 기본형 500,000 50,000 {middle_amounts} 100,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        middle_schedules = [schedule for schedule in options[0].payment_schedules if schedule.payment_type == "middle_payment"]
        self.assertEqual(len(middle_schedules), 10)
        self.assertEqual(middle_schedules[0].label, "중도금 1차")
        self.assertEqual(middle_schedules[-1].label, "중도금 10차")
        self.assertEqual(middle_schedules[-1].due_date.isoformat(), "2027-10-01")
        self.assertEqual(options[0].payment_schedules[-1].payment_type, "final_payment")
        self.assertEqual(options[0].loan_amount, 0)

    def test_rules_extractor_reads_residual_public_sale_installment_table(self):
        pages = [
            PdfPageText(
                page_no=4,
                text=(
                    "공급금액 및 대금납부조건 주택가격 계약금 잔금\n"
                    "[table 2]\n"
                    "주택형 타입 층별 주택가격 발코니확장비 계약시 계약일로부터 6개월 이내 입주잔금납부일로부터 5년 후 일시납\n"
                    "무상지원 계약금 입주잔금 융자금 (주택도시기금) 할부금 최대 선납할인금\n"
                    "055.9300A 55A 55AH 1층 257,040 6,321 10,000 115,180 55,000 76,860 19,215\n"
                    "2층 259,770 6,321 10,000 116,440 55,000 78,330 19,582"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertGreaterEqual(len(options), 2)
        first = options[0]
        self.assertEqual(first.unit_type, "55A")
        self.assertEqual(first.floor_group, "1층")
        self.assertEqual(first.base_price, 257040000)
        self.assertEqual(first.balcony_extension_price, 6321000)
        self.assertEqual(first.loan_amount, 55000000)
        self.assertEqual(
            [(schedule.label, schedule.payment_type, schedule.amount) for schedule in first.payment_schedules],
            [
                ("계약금", "down_payment", 10000000),
                ("입주잔금", "final_payment", 115180000),
                ("할부금", "installment_payment", 76860000),
            ],
        )

    def test_rules_extractor_reads_general_public_sale_multi_middle_table(self):
        pages = [
            PdfPageText(
                page_no=5,
                text=(
                    "공급금액 및 공급유형별 납부일정 계약금 중도금 잔금 분양가격\n"
                    "[table 3]\n"
                    "주택형 (주택타입) 층별 세대수 공급금액 계약금(10%) 중도금(60%) 잔금(30%)\n"
                    "계약시 1차(10%) 2차(10%) 3차(10%) 4차(10%) 5차(10%) 6차(10%) 입주 시 주택도시기금\n"
                    "’26.12.21. ’27.04.20. ’27.08.20. ’28.01.20. ’28.06.20. ’28.11.20.\n"
                    "059.9500A 59A 1층 9 463,450,000 46,345,000 46,345,000 46,345,000 46,345,000 46,345,000 46,345,000 46,345,000 84,035,000 55,000,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 1)
        option = options[0]
        self.assertEqual(option.unit_type, "59A")
        self.assertEqual(option.base_price, 463450000)
        self.assertEqual(option.loan_amount, 55000000)
        middle_schedules = [schedule for schedule in option.payment_schedules if schedule.payment_type == "middle_payment"]
        self.assertEqual(len(middle_schedules), 6)
        self.assertEqual(middle_schedules[0].due_date.isoformat(), "2026-12-21")
        self.assertEqual(middle_schedules[-1].label, "중도금 6차")
        self.assertEqual(option.payment_schedules[-1].amount, 84035000)

    def test_rules_extractor_keeps_final_payment_when_loan_header_has_blank_values(self):
        pages = [
            PdfPageText(
                page_no=5,
                text=(
                    "공공분양주택의 분양가격, 발코니 확장비용, 추가선택품목 공급가격\n"
                    "[table 2]\n"
                    "주택형 타입 층별 주택가격 계약금 (5%) 중도금 (20%) 잔금 융자금 (주택도시기금)\n"
                    "계약시 2028.02.14. 입주시\n"
                    "51A 1층 555,310,000 27,765,500 111,062,000 361,482,500\n"
                    "[table 3]\n"
                    "주택형 타입 층별 주택가격 계약금 (10%) 중도금 잔금 융자금 (주택도시기금)\n"
                    "1회차 (10%) 2회차 (10%)\n"
                    "계약시 2027.04.12. 2028.02.14 입주시\n"
                    "51A 1층 555,310,000 55,531,000 55,531,000 55,531,000 333,717,000"
                ),
            )
        ]

        options = extract_unit_options_from_pages(pages)

        self.assertEqual(len(options), 2)
        by_type = {option.option_type: option for option in options}
        self.assertEqual(
            [schedule.payment_type for schedule in by_type["pre_subscription"].payment_schedules],
            ["down_payment", "middle_payment", "final_payment"],
        )
        self.assertEqual(by_type["pre_subscription"].payment_schedules[-1].amount, 361482500)
        self.assertEqual(
            [schedule.payment_type for schedule in by_type["general_supply"].payment_schedules],
            ["down_payment", "middle_payment", "middle_payment", "final_payment"],
        )
        self.assertEqual(by_type["general_supply"].payment_schedules[-1].amount, 333717000)
        self.assertEqual(by_type["pre_subscription"].loan_amount, 55000000)
        self.assertEqual(by_type["general_supply"].loan_amount, 55000000)

    def test_rules_extractor_skips_additional_option_price_tables(self):
        pages = [
            PdfPageText(
                page_no=8,
                text=(
                    "추가선택품목 공급가격\n"
                    "천장형 시스템 에어컨 선택품목 계약금 중도금 잔금 공급가격\n"
                    "51A 800,000,000 880,000,000 800,000,000 780,000,000\n"
                    "63B 950,000,000 950,000,000 950,000,000 950,000,000"
                ),
            )
        ]

        self.assertEqual(extract_unit_options_from_pages(pages), [])

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

    def test_document_status_includes_needs_review_issues(self):
        document = NoticeDocument.objects.create(
            notice=self.notice,
            provider="LH",
            file_name="review.pdf",
            document_url="https://example.com/review.pdf",
            status="analyzed",
        )
        extraction = NoticeExtraction.objects.create(
            notice=self.notice,
            document=document,
            schema_version="rules-v1",
            status="needs_review",
            confidence=0.49,
            raw_json={
                "source": "rules",
                "warnings": {
                    "59A": ["계약금·중도금·잔금 합계와 분양가 차이가 큽니다."],
                },
            },
        )
        HousingUnitOption.objects.create(
            notice=self.notice,
            document=document,
            extraction=extraction,
            unit_type="59A",
            exclusive_area_m2=59,
            floor_group="1층",
            option_type="basic",
            base_price=500000000,
            confidence=0.49,
        )
        self.notice.official_document_status = "analyzed"
        self.notice.save(update_fields=["official_document_status"])

        response = self.client.get(f"/api/notices/{self.notice.id}/documents/status")
        summary = response.json()["analysis_summary"]

        self.assertEqual(summary["stage"], "needs_review")
        issue_codes = {issue["code"] for issue in summary["review_issues"]}
        self.assertIn("amount_mismatch", issue_codes)
        self.assertIn("low_confidence", issue_codes)
        self.assertIn("required_documents_missing", issue_codes)
        self.assertTrue(all(issue.get("action") for issue in summary["review_issues"]))
        self.assertTrue(all(issue.get("severity") for issue in summary["review_issues"]))

    @patch("apps.notice_docs.services.analysis.threading.Thread")
    def test_analyze_api_can_start_async_job(self, mock_thread):
        response = self.client.post(f"/api/notices/{self.notice.id}/documents/analyze?async=1")

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["official_document_status"], "pending")
        self.assertEqual(payload["document"]["status"], "pending")
        self.assertIn("analysis_summary", payload)
        mock_thread.return_value.start.assert_called_once()

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

    def test_sample_pdf_regression_command_writes_snapshot_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_path = f"{temp_dir}/expected.json"
            snapshot_path = f"{temp_dir}/snapshot.json"
            md_path = f"{temp_dir}/regression.md"
            with open(expected_path, "w", encoding="utf-8") as expected_file:
                json.dump(
                    {
                        "samples": [
                            {
                                "file_name": "rent_notice_506.pdf",
                                "kind": "exclude",
                                "ownership_type": "excluded",
                                "case_type": "lh_happy_house_rent",
                                "expected": {"exclude_keywords": ["행복주택", "임대"]},
                            }
                        ]
                    },
                    expected_file,
                    ensure_ascii=False,
                )

            call_command(
                "check_sample_pdf_regression",
                f"--expected={expected_path}",
                f"--snapshot-json={snapshot_path}",
                f"--report-md={md_path}",
                "--kind=exclude",
                "--max-samples=1",
            )

            with open(snapshot_path, encoding="utf-8") as snapshot_file:
                snapshot = json.load(snapshot_file)
            with open(md_path, encoding="utf-8") as md_file:
                markdown = md_file.read()

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["samples"][0]["file_name"], "rent_notice_506.pdf")
        self.assertEqual(snapshot["samples"][0]["stage"], "excluded_classified")
        self.assertIn("Sample PDF Regression", markdown)

    def test_sample_pdf_expected_manifest_covers_current_regression_samples(self):
        expected_path = settings.BASE_DIR / "fixtures" / "sample_pdfs" / "expected.json"
        data = json.loads(expected_path.read_text(encoding="utf-8"))
        samples = data["samples"]

        self.assertGreaterEqual(len(samples), 5)
        self.assertTrue(any(sample["kind"] == "include" for sample in samples))
        self.assertTrue(any(sample["kind"] == "exclude" for sample in samples))
        for sample in samples:
            self.assertTrue((settings.BASE_DIR / "fixtures" / "sample_pdfs" / sample["file_name"]).exists())
