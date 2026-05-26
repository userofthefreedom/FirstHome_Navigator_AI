from django.test import TestCase, override_settings

from apps.fixture_store import default_profile, find_notice, notices
from apps.funding.services.calculator import funding_plan
from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.models import HousingNotice
from apps.policies.models import YouthPolicy
from apps.policies.services.matcher import match_policies
from apps.products.models import FinancialProduct
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import ranked_recommendations


@override_settings(ROOT_URLCONF="config.urls")
class RecommendationServiceTests(TestCase):
    def test_representative_funding_uses_asset_as_available_cash(self):
        plan = funding_plan(101, default_profile())

        self.assertEqual(plan["price"], 320000000)
        self.assertEqual(plan["down_payment"], 32000000)
        self.assertEqual(plan["available_cash"], 8000000)
        self.assertEqual(plan["shortfall"], 24000000)
        self.assertEqual(plan["monthly_target"], 1333334)

    def test_fixture_has_enough_demo_data(self):
        self.assertGreaterEqual(len(notices(include_excluded=True)), 10)
        self.assertGreaterEqual(len(notices()), 3)
        self.assertTrue(all(notice["is_service_target"] for notice in notices()))
        self.assertGreaterEqual(len(match_products(default_profile(), limit=20)), 8)
        self.assertGreaterEqual(len(match_policies(default_profile(), limit=20)), 8)

    def test_top_recommendation_has_score_breakdown_and_reasons(self):
        top = ranked_recommendations(default_profile(), limit=3)[0]

        self.assertEqual(top["notice_id"], 101)
        self.assertEqual(top["notice_id"], find_notice(top["notice_id"])["id"])
        self.assertEqual(set(top["score_detail"]), {"eligibility", "funding", "location", "schedule", "policy_link"})
        self.assertEqual(top["total_score"], sum(top["score_detail"].values()))
        self.assertIn("analysis_summary", top)
        self.assertGreaterEqual(len(top["reasons"]), 3)

    def test_product_and_policy_matchers_change_by_profile(self):
        representative = default_profile()
        incheon_profile = {
            **representative,
            "preferred_regions": ["인천"],
            "preferred_supply_types": ["청년 공공주택"],
            "monthly_saving": 400000,
            "target_months": 12,
        }

        representative_policy_ids = [policy["id"] for policy in match_policies(representative)]
        incheon_policy_ids = [policy["id"] for policy in match_policies(incheon_profile)]
        representative_product_ids = [product["id"] for product in match_products(representative)]
        incheon_product_ids = [product["id"] for product in match_products(incheon_profile)]

        self.assertNotEqual(representative_policy_ids, incheon_policy_ids)
        self.assertNotEqual(representative_product_ids, incheon_product_ids)

    def test_db_data_is_used_before_fixture_when_available(self):
        notice = HousingNotice.objects.create(
            id=999,
            title="DB 우선 공고",
            provider="테스트",
            region="서울",
            district="서울 테스트구",
            supply_type="뉴홈",
            housing_type="공공분양",
            area="59m2",
            price=320000000,
            contract_rate=0.1,
            application_deadline="2026-06-01",
            winner_date="2026-06-10",
            contract_date="2026-07-01",
            move_in="2028-01",
            competition="테스트",
            source_url="https://example.com",
            tags=["청년", "생애최초"],
            required_documents=["주민등록등본"],
            cautions=["공식 확인 필요"],
        )
        FinancialProduct.objects.create(
            id=999,
            name="DB 우선 적금",
            provider="테스트은행",
            category="적금",
            rate="연 4.00%",
            monthly_limit=1000000,
            term_months=18,
            protection_status=True,
            source_url="https://example.com",
            reasons=["DB 상품입니다."],
        )
        YouthPolicy.objects.create(
            id=999,
            name="DB 우선 정책",
            provider="테스트기관",
            target="청년",
            benefit="상담",
            policy_category="상담",
            regions=["서울"],
            age_min=19,
            age_max=39,
            max_income=50000000,
            requires_homeless=False,
            source_url="https://example.com",
            reasons=["DB 정책입니다."],
        )

        self.assertEqual(notices()[0]["id"], 999)
        self.assertEqual(match_products(default_profile(), limit=1)[0]["id"], 999)
        self.assertEqual(match_policies(default_profile(), limit=1)[0]["id"], 999)

        option = HousingUnitOption.objects.create(
            notice=notice,
            unit_type="59A",
            exclusive_area_m2=59.7,
            floor_group="5층~최상층",
            option_type="basic",
            base_price=315000000,
            confidence=0.9,
        )
        PaymentSchedule.objects.create(
            unit_option=option,
            label="계약금",
            amount=31500000,
            payment_type="down_payment",
            sequence=1,
        )

        recommendation = ranked_recommendations(default_profile(), limit=1)[0]
        self.assertEqual(recommendation["best_option"]["option_id"], option.id)
        self.assertEqual(recommendation["top_options"][0]["option_id"], option.id)
        self.assertGreater(recommendation["best_option"]["option_fit_score"], 0)
        self.assertGreaterEqual(len(recommendation["best_option"]["fit_reasons"]), 1)

    @override_settings(FIRSTHOME_FIXTURE_FALLBACK={"ENABLE_SUPPLEMENT": True, "MIN_SERVICE_NOTICES": 3})
    def test_fixture_supplements_when_real_service_notices_are_too_few(self):
        HousingNotice.objects.create(
            id=998,
            source_id="LH-REAL-ONE",
            title="실제 LH 공공분양 1건",
            provider="LH",
            region="경기 남부",
            district="남양주",
            supply_type="공공분양",
            housing_type="분양주택",
            area="59.95",
            price=493040000,
            contract_rate=0.1,
            application_deadline="2026-06-01",
            winner_date="2026-06-10",
            contract_date="2026-07-01",
            move_in="2028-01",
            competition="350호",
            source_url="https://apply.lh.or.kr",
            tags=["LH", "공공분양"],
            required_documents=[],
            cautions=[],
            ownership_type="public_sale",
            is_service_target=True,
        )

        service_notices = notices()

        self.assertEqual(service_notices[0]["id"], 998)
        self.assertGreaterEqual(len(service_notices), 3)
        self.assertTrue(any(notice["data_source"] == "fixture fallback" for notice in service_notices[1:]))

    @override_settings(FIRSTHOME_FIXTURE_FALLBACK={"ENABLE_SUPPLEMENT": False, "MIN_SERVICE_NOTICES": 3})
    def test_fixture_supplement_can_be_disabled(self):
        HousingNotice.objects.create(
            id=997,
            source_id="LH-REAL-ONLY",
            title="실제 LH 공공분양 단독",
            provider="LH",
            region="경기 남부",
            district="남양주",
            supply_type="공공분양",
            housing_type="분양주택",
            area="59.95",
            price=493040000,
            contract_rate=0.1,
            application_deadline="2026-06-01",
            winner_date="2026-06-10",
            contract_date="2026-07-01",
            move_in="2028-01",
            competition="350호",
            source_url="https://apply.lh.or.kr",
            tags=["LH", "공공분양"],
            required_documents=[],
            cautions=[],
            ownership_type="public_sale",
            is_service_target=True,
        )

        self.assertEqual([notice["id"] for notice in notices()], [997])
