from django.test import SimpleTestCase

from apps.products.services.finlife import normalize_finlife_products


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
