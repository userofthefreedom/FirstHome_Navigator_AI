from django.test import TestCase

from apps.notice_docs.models import HousingUnitOption, NoticeDocument, PaymentSchedule
from apps.notice_docs.services import analyze_notice_with_mock_data
from apps.notices.models import HousingNotice


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
