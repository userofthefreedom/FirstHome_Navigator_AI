from django.test import SimpleTestCase

from apps.products.services.finlife import normalize_finlife_loan_products, normalize_finlife_products


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
