from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.fixture_store import default_profile
from apps.products.models import FinancialProduct, UserJoinedProduct
from apps.products.services.finlife import normalize_finlife_loan_products, normalize_finlife_product_records, normalize_finlife_products
from apps.products.services.matcher import match_products


class FinlifeNormalizerTests(SimpleTestCase):
    def test_deposit_product_is_normalized_per_term_option(self):
        result = {
            "baseList": [
                {
                    "fin_prdt_cd": "D001",
                    "kor_co_nm": "테스트은행",
                    "fin_prdt_nm": "첫집 예금",
                    "join_way": "영업점, 인터넷",
                    "max_limit": None,
                }
            ],
            "optionList": [
                {"fin_prdt_cd": "D001", "save_trm": "12", "intr_rate": "3.1", "intr_rate2": "3.5"},
                {"fin_prdt_cd": "D001", "save_trm": "24", "intr_rate": "3.2", "intr_rate2": "3.7"},
            ],
        }

        products = normalize_finlife_products(result, "deposit")

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].name, "첫집 예금 (12개월)")
        self.assertEqual(products[0].provider, "테스트은행")
        self.assertEqual(products[0].category, "예금")
        self.assertEqual(products[0].rate, "최고 연 3.50%")
        self.assertEqual(products[0].monthly_limit, 0)

    def test_saving_product_keeps_monthly_limit(self):
        result = {
            "baseList": [
                {
                    "fin_prdt_cd": "S001",
                    "kor_co_nm": "테스트은행",
                    "fin_prdt_nm": "첫집 적금",
                    "join_way": "스마트폰",
                    "max_limit": "1000000",
                }
            ],
            "optionList": [
                {"fin_prdt_cd": "S001", "save_trm": "18", "intr_rate": "4.0", "intr_rate2": "4.2"},
            ],
        }

        products = normalize_finlife_products(result, "saving")

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "첫집 적금 (18개월)")
        self.assertEqual(products[0].category, "적금")
        self.assertEqual(products[0].monthly_limit, 1000000)
        self.assertIn("금융감독원", products[0].reasons[0])

    def test_finlife_product_records_keep_terms_as_options(self):
        result = {
            "baseList": [
                {
                    "fin_prdt_cd": "D001",
                    "fin_co_no": "001",
                    "kor_co_nm": "테스트은행",
                    "fin_prdt_nm": "첫집 예금",
                    "join_way": "영업점, 인터넷",
                    "max_limit": None,
                }
            ],
            "optionList": [
                {"fin_prdt_cd": "D001", "save_trm": "12", "intr_rate": "3.1", "intr_rate2": "3.5"},
                {"fin_prdt_cd": "D001", "save_trm": "24", "intr_rate": "3.2", "intr_rate2": "3.7"},
            ],
        }

        records = normalize_finlife_product_records(result, "deposit")

        self.assertEqual(len(records), 2)
        self.assertEqual({record["name"] for record in records}, {"첫집 예금"})
        self.assertEqual({record["option"]["save_trm"] for record in records}, {12, 24})
        self.assertTrue(all(record["category"] == "예금" for record in records))

    def test_mortgage_loan_product_is_normalized_for_purchase_matching(self):
        result = {
            "baseList": [
                {
                    "fin_prdt_cd": "M001",
                    "kor_co_nm": "테스트은행",
                    "fin_prdt_nm": "첫집 주택담보대출",
                    "join_way": "영업점, 인터넷",
                    "loan_lmt": "최대 3억원",
                    "loan_inci_expn": "인지세 등",
                    "erly_rpay_fee": "3년 이내 1.2%",
                    "dly_rate": "약정금리+3%",
                }
            ],
            "optionList": [
                {
                    "fin_prdt_cd": "M001",
                    "mrtg_type_nm": "아파트",
                    "rpay_type_nm": "원리금분할상환",
                    "lend_rate_type_nm": "고정금리",
                    "lend_rate_min": "3.2",
                    "lend_rate_max": "4.1",
                    "lend_rate_avg": "3.7",
                }
            ],
        }

        products = normalize_finlife_loan_products(result, "mortgage")

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].provider, "테스트은행")
        self.assertEqual(products[0].category, "주택담보대출")
        self.assertEqual(products[0].loan_purpose, "purchase")
        self.assertEqual(products[0].limit_amount, 300000000)
        self.assertEqual(products[0].rate, "최저 연 3.20% ~ 최고 연 4.10%")
        self.assertIn("원리금분할상환", products[0].reasons[1])


class FinancialProductApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.saving_24 = FinancialProduct.objects.create(
            name="첫집 적금 (24개월)",
            provider="테스트은행",
            category="적금",
            rate="최고 연 4.20%",
            monthly_limit=0,
            term_months=24,
            source_url="https://example.com/saving-24",
        )
        self.saving_12 = FinancialProduct.objects.create(
            name="첫집 적금 (12개월)",
            provider="테스트은행",
            category="적금",
            rate="최고 연 3.80%",
            monthly_limit=0,
            term_months=12,
            source_url="https://example.com/saving-12",
        )
        self.deposit_24 = FinancialProduct.objects.create(
            name="첫집 예금 (24개월)",
            provider="테스트은행",
            category="예금",
            rate="최고 연 3.90%",
            monthly_limit=0,
            term_months=24,
            source_url="https://example.com/deposit-24",
        )

    def test_product_category_filter_accepts_frontend_aliases(self):
        deposit_response = self.client.get("/api/products", {"category": "deposit"})
        saving_response = self.client.get("/api/products", {"category": "saving"})

        self.assertEqual(deposit_response.status_code, 200)
        self.assertEqual(saving_response.status_code, 200)
        self.assertEqual({item["category"] for item in deposit_response.data["items"]}, {"예금"})
        self.assertEqual({item["category"] for item in saving_response.data["items"]}, {"적금"})
        self.assertTrue(all(item["option_count"] == 1 for item in saving_response.data["items"]))

    def test_fit_order_uses_product_matcher_order(self):
        expected_ids = [item["id"] for item in match_products(default_profile(), limit=3)]
        response = self.client.get("/api/products", {"ordering": "fit"})
        actual_ids = [item["id"] for item in response.data["items"][:3]]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(actual_ids, expected_ids)

    def test_fit_score_uses_expanded_scale(self):
        response = self.client.get("/api/products", {"ordering": "fit"})
        scores = [item["match_score"] for item in response.data["items"]]

        self.assertEqual(response.status_code, 200)
        self.assertGreater(max(scores), 30)
        self.assertGreater(len(set(scores)), 1)

    def test_joined_product_delete_only_removes_current_user_item(self):
        user = get_user_model().objects.create_user(username="joined-user", password="pw")
        other_user = get_user_model().objects.create_user(username="other-user", password="pw")
        joined = UserJoinedProduct.objects.create(user=user, product=self.saving_24)
        other_joined = UserJoinedProduct.objects.create(user=other_user, product=self.deposit_24)

        self.client.force_authenticate(user=user)
        other_response = self.client.delete(f"/api/products/joined/{other_joined.id}")
        own_response = self.client.delete(f"/api/products/joined/{joined.id}")

        self.assertEqual(other_response.status_code, 404)
        self.assertEqual(own_response.status_code, 204)
        self.assertFalse(UserJoinedProduct.objects.filter(id=joined.id).exists())
        self.assertTrue(UserJoinedProduct.objects.filter(id=other_joined.id).exists())
