from django.test import TestCase

from apps.funding.services.calculator import funding_plan
from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.models import HousingNotice


class OptionFundingPlanTests(TestCase):
    def setUp(self):
        self.notice = HousingNotice.objects.create(
            title="옵션 기반 공공분양",
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
            is_service_target=True,
            ownership_type="public_sale",
        )
        self.option = HousingUnitOption.objects.create(
            notice=self.notice,
            unit_type="59A",
            exclusive_area_m2=59.72,
            floor_group="5층~최상층",
            option_type="basic",
            base_price=526340000,
            loan_amount=55000000,
            confidence=0.8,
        )
        PaymentSchedule.objects.create(
            unit_option=self.option,
            label="계약금",
            due_date="2026-07-01",
            amount=52634000,
            payment_type="down_payment",
            sequence=1,
        )
        PaymentSchedule.objects.create(
            unit_option=self.option,
            label="중도금 1차",
            due_date="2027-12-08",
            amount=52634000,
            payment_type="middle_payment",
            sequence=2,
        )
        PaymentSchedule.objects.create(
            unit_option=self.option,
            label="잔금",
            amount=155000000,
            payment_type="final_payment",
            sequence=3,
        )

    def test_funding_plan_uses_payment_schedule_when_option_id_is_given(self):
        plan = funding_plan(
            self.notice.id,
            {"asset": 10000000, "target_months": 12},
            option_id=self.option.id,
        )

        self.assertEqual(plan["schedule_source"], "payment_schedule")
        self.assertEqual(plan["option_id"], self.option.id)
        self.assertEqual(plan["price"], 526340000)
        self.assertEqual(plan["down_payment"], 52634000)
        self.assertEqual(plan["shortfall"], 42634000)
        self.assertEqual(len(plan["timeline"]), 3)

    def test_funding_api_accepts_option_id_query_param(self):
        response = self.client.get(f"/api/recommendations/funding/{self.notice.id}?option_id={self.option.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schedule_source"], "payment_schedule")
        self.assertEqual(response.json()["unit_type"], "59A")
