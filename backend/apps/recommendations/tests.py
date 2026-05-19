from django.test import SimpleTestCase, override_settings

from apps.fixture_store import default_profile, find_notice, notices
from apps.funding.services.calculator import funding_plan
from apps.policies.services.matcher import match_policies
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import ranked_recommendations


@override_settings(ROOT_URLCONF="config.urls")
class RecommendationServiceTests(SimpleTestCase):
    def test_representative_funding_uses_asset_as_available_cash(self):
        plan = funding_plan(101, default_profile())

        self.assertEqual(plan["price"], 320000000)
        self.assertEqual(plan["down_payment"], 32000000)
        self.assertEqual(plan["available_cash"], 8000000)
        self.assertEqual(plan["shortfall"], 24000000)
        self.assertEqual(plan["monthly_target"], 1333334)

    def test_fixture_has_enough_demo_data(self):
        self.assertGreaterEqual(len(notices()), 10)
        self.assertGreaterEqual(len(match_products(default_profile(), limit=20)), 8)
        self.assertGreaterEqual(len(match_policies(default_profile(), limit=20)), 8)

    def test_top_recommendation_has_score_breakdown_and_reasons(self):
        top = ranked_recommendations(default_profile(), limit=3)[0]

        self.assertEqual(top["notice_id"], 101)
        self.assertEqual(top["notice_id"], find_notice(top["notice_id"])["id"])
        self.assertEqual(set(top["score_detail"]), {"eligibility", "funding", "location", "schedule", "policy_link"})
        self.assertEqual(top["total_score"], sum(top["score_detail"].values()))
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
