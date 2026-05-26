from datetime import date

from django.test import SimpleTestCase
from django.core.management import call_command
from django.test import TestCase

from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.management.commands.import_lh import Command as ImportLhCommand
from apps.notices.models import HousingNotice
from apps.notices.services.classifier import classify_notice_payload
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

    def test_supply_info_summary_extracts_sale_unit_options(self):
        payload = [
            {"dsSch": [{"PAN_ID": "LH-SALE"}]},
            {
                "dsList01Nm": [{"HTY_NM": "주택형", "SIL_AMT": "평균분양가격(원)"}],
                "dsList01": [
                    {
                        "RSDN_DDO_AR": "59.95",
                        "BZDT_NM": "남양주왕숙2 A01",
                        "SIL_HSH_CNT": "350",
                        "HTY_NM": "59.9500A",
                        "SPL_AR": "82.4497",
                        "SIL_AMT": "493040000",
                    },
                    {
                        "RSDN_DDO_AR": "74.91",
                        "BZDT_NM": "남양주왕숙2 A01",
                        "SIL_HSH_CNT": "73",
                        "HTY_NM": "74.9100A",
                        "SPL_AR": "103.0243",
                        "SIL_AMT": "613680000",
                    },
                ],
            },
        ]

        summary = supply_info_summary(payload)

        self.assertEqual(summary["area"], "59.95, 74.91")
        self.assertEqual(summary["price"], 613680000)
        self.assertEqual(summary["unit_options"][0]["unit_type"], "59A")
        self.assertEqual(summary["unit_options"][0]["base_price"], 493040000)
        self.assertEqual(summary["unit_options"][1]["unit_type"], "74A")

    def test_classifier_keeps_residual_public_sale_in_service_scope(self):
        classification = classify_notice_payload(
            {
                "title": "울산다운2 신혼희망타운(공공분양) 추가입주자모집공고",
                "supply_type": "공공분양",
                "housing_type": "공공분양주택",
                "tags": ["잔여세대", "선착순 동호지정"],
            }
        )

        self.assertTrue(classification.is_service_target)
        self.assertEqual(classification.ownership_type, "newlywed_public_sale")

    def test_classifier_excludes_officetel_sale_notice(self):
        classification = classify_notice_payload(
            {
                "title": "아산배방 LH4단지 오피스텔 잔여세대 선착순 동호지정 공고",
                "supply_type": "분양",
                "housing_type": "오피스텔",
            }
        )

        self.assertFalse(classification.is_service_target)
        self.assertEqual(classification.ownership_type, "excluded")
        self.assertIn("오피스텔", classification.exclude_reason)


class FirstHomeFixtureLoaderTests(TestCase):
    def test_fixture_loader_persists_service_target_classification(self):
        call_command("load_firsthome_fixture", verbosity=0)

        notice = HousingNotice.objects.get(id=101)

        self.assertTrue(notice.is_service_target)
        self.assertIn(notice.ownership_type, {"public_sale", "newlywed_public_sale", "private_participation_public_sale"})


class ImportLhSupplyOptionTests(TestCase):
    def test_supply_summary_seeds_temporary_unit_options_and_payment_schedules(self):
        notice = HousingNotice.objects.create(
            source_id="LH-SALE",
            title="남양주왕숙2 A-3BL 공공분양주택 입주자모집공고",
            provider="LH",
            region="경기 남부",
            district="남양주",
            supply_type="공공분양",
            housing_type="분양주택",
            area="59.95",
            price=613680000,
            contract_rate=0.1,
            application_deadline=date(2026, 6, 30),
            winner_date=date(2026, 7, 14),
            contract_date=date(2026, 7, 30),
            move_in="공식 확인 필요",
            ownership_type="public_sale",
            is_service_target=True,
        )
        summary = {
            "unit_options": [
                {
                    "unit_type": "59A",
                    "raw_unit_type": "59.9500A",
                    "exclusive_area_m2": 59.95,
                    "base_price": 493040000,
                }
            ]
        }

        ImportLhCommand()._sync_supply_options(notice, summary)

        option = HousingUnitOption.objects.get(notice=notice, unit_type="59A")
        self.assertEqual(option.base_price, 493040000)
        self.assertIn("LH 공급정보 API", option.source_text)
        self.assertEqual(PaymentSchedule.objects.filter(unit_option=option).count(), 3)
        self.assertEqual(
            PaymentSchedule.objects.get(unit_option=option, payment_type="down_payment").amount,
            49304000,
        )
