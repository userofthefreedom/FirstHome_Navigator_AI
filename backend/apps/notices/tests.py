from django.test import SimpleTestCase

from apps.notices.services.lh import normalize_lh_notices, supply_info_summary


class LhNoticeNormalizerTests(SimpleTestCase):
    def test_housing_notice_is_normalized(self):
        payload = [
            {"dsSch": [{"PAGE": "1", "PG_SZ": "2"}]},
            {
                "dsList": [
                    {
                        "PAN_ID": "LH-001",
                        "PAN_NM": "서울 청년 행복주택 입주자 모집",
                        "AIS_TP_CD_NM": "행복주택",
                        "UPP_AIS_TP_NM": "임대주택",
                        "CNP_CD_NM": "서울특별시",
                        "CLSG_DT": "2026.06.30",
                        "DTL_URL": "https://apply.lh.or.kr/detail",
                        "ALL_CNT": "2",
                    }
                ]
            },
        ]

        notices = normalize_lh_notices(payload)

        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].source_id, "LH-001")
        self.assertEqual(notices[0].region, "서울")
        self.assertEqual(notices[0].supply_type, "청년 공공주택")
        self.assertEqual(notices[0].price, 0)
        self.assertEqual(notices[0].source_meta["pan_id"], "LH-001")
        self.assertIn("공식 공고문", notices[0].cautions[0])

    def test_land_and_commercial_notices_are_skipped(self):
        payload = [
            {
                "dsList": [
                    {
                        "PAN_ID": "LAND-001",
                        "PAN_NM": "성남 상업용지 공급공고",
                        "AIS_TP_CD_NM": "토지",
                        "UPP_AIS_TP_NM": "토지",
                        "CNP_CD_NM": "경기도",
                        "CLSG_DT": "2026.06.30",
                    },
                    {
                        "PAN_ID": "SHOP-001",
                        "PAN_NM": "단지내상가 분양공고",
                        "AIS_TP_CD_NM": "분양ㆍ임대상가",
                        "UPP_AIS_TP_NM": "상가",
                        "CNP_CD_NM": "부산광역시",
                        "CLSG_DT": "2026.06.30",
                    },
                ]
            }
        ]

        self.assertEqual(normalize_lh_notices(payload), [])

    def test_supply_info_summary_extracts_area_price_and_units(self):
        payload = [
            {"dsSch": [{"PAN_ID": "LH-001"}]},
            {
                "dsList01": [
                    {
                        "DDO_AR": "36.12",
                        "SPL_AR": "51.2345",
                        "HTY_NNA": "36A 청년",
                        "LS_GMY": "120000000",
                        "HSH_CNT": "10",
                        "SBD_LGO_NM": "서울 강동 행복주택",
                    },
                    {
                        "DDO_AR": "44.95",
                        "HTY_NNA": "44B 신혼부부",
                        "LS_GMY": "공고문 참조",
                        "RFE": "150000000",
                        "HSH_CNT": "5",
                        "SBD_LGO_NM": "서울 강동 행복주택",
                    },
                ]
            },
        ]

        summary = supply_info_summary(payload)

        self.assertEqual(summary["area"], "36.12, 44.95")
        self.assertEqual(summary["price"], 150000000)
        self.assertEqual(summary["housing_type"], "36A 청년")
        self.assertEqual(summary["district"], "서울 강동 행복주택")
        self.assertEqual(summary["competition"], "15호")
