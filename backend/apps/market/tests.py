from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.market.models import MarketAssetPrice


class MarketAssetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        MarketAssetPrice.objects.create(
            asset_type="estate_apt_trade_avg",
            base_date=date(2026, 5, 1),
            region_code="11110",
            region_name="서울 종로구",
            price=100000,
            source="test",
            source_meta={"unit": "만원"},
        )
        MarketAssetPrice.objects.create(
            asset_type="estate_apt_trade_avg",
            base_date=date(2026, 5, 1),
            region_code="11680",
            region_name="서울 강남구",
            price=200000,
            source="test",
            source_meta={"unit": "만원"},
        )

    def test_estate_asset_without_region_returns_grouped_average(self):
        response = self.client.get("/api/market/assets", {"asset": "estate_apt_trade_avg"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["label"], "전국 아파트 평균 실거래가")
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["price"], 150000)
        self.assertEqual(len(response.data["regions"]), 2)

    def test_estate_asset_supports_region_prefix_and_region_code(self):
        prefix_response = self.client.get("/api/market/assets", {"asset": "estate_apt_trade_avg", "region_prefix": "11"})
        region_response = self.client.get("/api/market/assets", {"asset": "estate_apt_trade_avg", "region": "11680"})

        self.assertEqual(prefix_response.data["items"][0]["price"], 150000)
        self.assertEqual(region_response.data["label"], "서울 강남구 아파트 평균 실거래가")
        self.assertEqual(region_response.data["items"][0]["price"], 200000)
