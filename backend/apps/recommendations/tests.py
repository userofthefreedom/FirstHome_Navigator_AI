from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase, override_settings

from apps.fixture_store import current_notices, default_profile, find_notice, notices
from apps.funding.services.calculator import funding_plan
from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.models import HousingNotice
from apps.policies.models import YouthPolicy
from apps.policies.services.matcher import match_policies
from apps.products.models import FinancialProduct
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import ranked_recommendations
from apps.rules.confidence import option_confidence_from_quality
from apps.rules.funding import ceil_divide, default_payment_amounts
from apps.rules.document_discovery import document_candidate_priority
from apps.rules.retrieval import query_terms, rank_document_chunk
from apps.rules.scoring import location_score, option_fit_score, option_funding_insights, option_type_priority


class SharedRuleTests(SimpleTestCase):
    def test_funding_amount_rules_are_shared(self):
        amounts = default_payment_amounts(500_000_000, contract_rate=0.1, middle_payment_rate=0.6)

        self.assertEqual(amounts["down_payment"], 50_000_000)
        self.assertEqual(amounts["middle_payment"], 300_000_000)
        self.assertEqual(amounts["final_payment"], 150_000_000)
        self.assertEqual(ceil_divide(42_634_000, 12), 3_552_834)

    def test_option_scoring_rules_prefer_general_supply(self):
        option = {
            "exclusive_area_m2": 59,
            "base_price": 526_340_000,
            "down_payment": 52_634_000,
            "middle_payment": 315_804_000,
        }
        profile = {
            "desired_area_min_m2": 50,
            "desired_area_max_m2": 60,
            "desired_price_max": 600_000_000,
            "max_down_payment": 60_000_000,
            "monthly_payment_capacity": 20_000_000,
        }

        self.assertGreater(option_fit_score(option, profile), 80)
        self.assertGreater(option_type_priority("general_supply"), option_type_priority("pre_subscription"))

    def test_option_scoring_uses_payment_schedule_span(self):
        profile = {
            "desired_area_min_m2": 50,
            "desired_area_max_m2": 60,
            "desired_price_max": 600_000_000,
            "max_down_payment": 60_000_000,
            "monthly_payment_capacity": 6_000_000,
        }
        common_option = {
            "exclusive_area_m2": 59,
            "base_price": 500_000_000,
            "down_payment": 50_000_000,
        }
        compressed_option = {
            **common_option,
            "payment_schedules": [
                {"payment_type": "middle_payment", "amount": 60_000_000, "due_date": "2027-01-01"},
                {"payment_type": "middle_payment", "amount": 60_000_000, "due_date": "2027-02-01"},
            ],
        }
        spread_option = {
            **common_option,
            "payment_schedules": [
                {"payment_type": "middle_payment", "amount": 60_000_000, "due_date": "2027-01-01"},
                {"payment_type": "middle_payment", "amount": 60_000_000, "due_date": "2028-12-01"},
            ],
        }

        self.assertLess(option_fit_score(compressed_option, profile), option_fit_score(spread_option, profile))

    def test_option_funding_insights_explain_down_payment_and_loan(self):
        option = {
            "exclusive_area_m2": 59,
            "base_price": 500_000_000,
            "loan_amount": 55_000_000,
            "payment_schedules": [
                {"payment_type": "down_payment", "amount": 50_000_000, "due_date": "2026-07-01"},
                {"payment_type": "middle_payment", "amount": 120_000_000, "due_date": "2027-01-01"},
                {"payment_type": "middle_payment", "amount": 120_000_000, "due_date": "2027-07-01"},
                {"payment_type": "final_payment", "amount": 205_000_000, "due_date": ""},
            ],
        }
        profile = {
            "asset": 8_000_000,
            "max_down_payment": 40_000_000,
            "monthly_payment_capacity": 8_000_000,
            "target_months": 10,
        }

        insights = option_funding_insights(option, profile)

        self.assertEqual(insights["down_payment_shortfall"], 10_000_000)
        self.assertEqual(insights["down_payment_monthly_target"], 1_000_000)
        self.assertTrue(insights["has_post_balance_loan"])
        self.assertTrue(insights["can_handle_post_balance_loan"])
        self.assertGreater(insights["monthly_schedule_need"], 0)
        self.assertGreater(insights["move_in_cash_gap"], 0)

    def test_document_discovery_rules_prefer_notice_pdf(self):
        notice_score = document_candidate_priority("시흥하중 A1블록 입주자모집공고문.pdf")
        brochure_score = document_candidate_priority("단지 팸플릿.pdf")

        self.assertGreater(notice_score, brochure_score)

    def test_retrieval_rules_prioritize_money_tables(self):
        terms = query_terms("계약금 중도금 잔금", ["주택가격"])
        table_score, matched = rank_document_chunk("주택형 주택가격 계약금 중도금 잔금 59A 500,000,000", "table", terms)
        paragraph_score, _matched = rank_document_chunk("공고 일반 안내입니다.", "paragraph", terms)

        self.assertGreater(table_score, paragraph_score)
        self.assertIn("계약금", matched)

    def test_confidence_rules_cap_options_with_validation_warnings(self):
        confidence = option_confidence_from_quality(
            base_confidence=0.88,
            has_price=True,
            has_schedule=False,
            has_source=True,
            has_required_schedule_types=False,
            validation_warnings=["납부 일정이 없습니다."],
        )

        self.assertLessEqual(confidence, 0.49)


@override_settings(ROOT_URLCONF="config.urls")
class RecommendationServiceTests(TestCase):
    def test_representative_funding_uses_asset_as_available_cash(self):
        plan = funding_plan(101, default_profile())

        self.assertEqual(plan["price"], 520000000)
        self.assertEqual(plan["down_payment"], 52000000)
        self.assertEqual(plan["available_cash"], 8000000)
        self.assertEqual(plan["shortfall"], 44000000)
        self.assertEqual(plan["monthly_target"], 2444445)

    def test_fixture_has_enough_demo_data(self):
        presentation_date = date(2026, 6, 26)
        self.assertGreaterEqual(len(notices(include_excluded=True)), 85)
        self.assertGreaterEqual(len(notices()), 85)
        self.assertTrue(all(notice["is_service_target"] for notice in notices()))
        self.assertTrue(all(date.fromisoformat(notice["application_deadline"]) > presentation_date for notice in notices()))
        regions = {notice["region"] for notice in notices()}
        self.assertGreaterEqual(len(regions), 17)
        for region in regions:
            self.assertGreaterEqual(sum(1 for notice in notices() if notice["region"] == region), 5)
        self.assertGreaterEqual(len(match_products(default_profile(), limit=20)), 8)
        self.assertGreaterEqual(len(match_policies(default_profile(), limit=20)), 8)

    def test_gyeonggi_split_preferences_include_gyeonggi_fixture_notices(self):
        profile = {
            **default_profile(),
            "preferred_regions": ["경기 남부", "경기 북부"],
        }

        recommendations = ranked_recommendations(profile, limit=20)

        self.assertTrue(recommendations)
        self.assertTrue(any(item["region"] == "경기" for item in recommendations))
        self.assertTrue(all("경기" in f"{item['region']} {item['district']} {item['title']}" for item in recommendations))

    def test_top_recommendation_has_score_breakdown_and_reasons(self):
        top = ranked_recommendations(default_profile(), limit=3)[0]

        self.assertEqual(top["notice_id"], find_notice(top["notice_id"])["id"])
        self.assertEqual(set(top["score_detail"]), {"eligibility", "funding", "location", "schedule"})
        self.assertEqual(top["total_score"], sum(top["score_detail"].values()))
        self.assertEqual(top["score_max"], 100)
        if top["data_source"] == "fixture":
            self.assertLessEqual(top["total_score"], 70)
        self.assertIn("analysis_summary", top)
        self.assertGreaterEqual(len(top["reasons"]), 3)
        self.assertGreaterEqual(len(top["explanations"]), 1)
        self.assertTrue(top["selection_summary"])

    def test_expired_notices_are_excluded_from_current_candidates(self):
        yesterday = date.today() - timedelta(days=1)
        HousingNotice.objects.create(
            id=996,
            source_id="LH-EXPIRED",
            title="마감 지난 고득점 공고",
            provider="LH",
            region="인천",
            district="인천 테스트구",
            supply_type="공공분양",
            housing_type="분양주택",
            area="84m2",
            price=330000000,
            contract_rate=0.1,
            application_deadline=yesterday,
            winner_date=date.today() + timedelta(days=7),
            contract_date=date.today() + timedelta(days=30),
            move_in="2028-01",
            competition="100호",
            source_url="https://example.com",
            tags=["LH", "공공분양"],
            required_documents=["주민등록등본"],
            cautions=["공식 확인 필요"],
            ownership_type="public_sale",
            is_service_target=True,
        )

        current_ids = [notice["id"] for notice in current_notices(include_excluded=True)]
        recommendation_ids = [item["notice_id"] for item in ranked_recommendations(default_profile(), limit=20)]

        self.assertNotIn(996, current_ids)
        self.assertNotIn(996, recommendation_ids)

    def test_recommendations_keep_only_latest_correction_notice(self):
        deadline = date.today() + timedelta(days=30)
        common_fields = {
            "provider": "LH",
            "region": "경기 남부",
            "district": "남양주왕숙2 A03",
            "supply_type": "공공분양",
            "housing_type": "59.0000A",
            "area": "59.72",
            "price": 526340000,
            "contract_rate": 0.1,
            "application_deadline": deadline,
            "winner_date": deadline + timedelta(days=14),
            "contract_date": deadline + timedelta(days=30),
            "move_in": "2028-01",
            "competition": "686호",
            "source_url": "https://apply.lh.or.kr",
            "tags": ["LH", "공공분양"],
            "required_documents": [],
            "cautions": [],
            "ownership_type": "public_sale",
            "is_service_target": True,
        }
        HousingNotice.objects.create(
            id=991,
            source_id="0000061082",
            title="남양주왕숙2 A-3BL 공공분양주택 입주자모집공고",
            source_meta={"pan_id": "0000061082"},
            **common_fields,
        )
        HousingNotice.objects.create(
            id=992,
            source_id="0000061086",
            title="[정정공고]남양주왕숙2 A-3BL 공공분양주택 입주자모집공고",
            source_meta={"pan_id": "0000061086"},
            **common_fields,
        )
        HousingNotice.objects.create(
            id=993,
            source_id="0000061089",
            title="[정정공고][정정공고]남양주왕숙2 A-3BL 공공분양주택 입주자모집공고",
            source_meta={"pan_id": "0000061089"},
            **common_fields,
        )

        profile = {**default_profile(), "preferred_regions": []}
        recommendation_ids = [item["notice_id"] for item in ranked_recommendations(profile, limit=20)]

        self.assertIn(993, recommendation_ids)
        self.assertNotIn(991, recommendation_ids)
        self.assertNotIn(992, recommendation_ids)

    def test_recommendations_collapse_same_notice_with_trailing_qualifier(self):
        deadline = date.today() + timedelta(days=30)
        common_fields = {
            "provider": "LH",
            "region": "경기 남부",
            "district": "경기도",
            "supply_type": "공공분양",
            "housing_type": "매입임대",
            "area": "공식 공고 확인",
            "price": 0,
            "contract_rate": 0.1,
            "application_deadline": deadline,
            "winner_date": deadline + timedelta(days=14),
            "contract_date": deadline + timedelta(days=30),
            "move_in": "공식 공고 확인",
            "competition": "LH 공고",
            "source_url": "https://apply.lh.or.kr",
            "tags": ["LH", "공공분양"],
            "required_documents": [],
            "cautions": [],
            "ownership_type": "public_sale",
            "is_service_target": True,
        }
        HousingNotice.objects.create(
            id=987,
            source_id="2015122300019987",
            title="[경기북부] 남양주왕숙2 A-3BL 공공분양주택 입주자 모집공고",
            source_meta={"pan_id": "2015122300019987"},
            **common_fields,
        )
        HousingNotice.objects.create(
            id=902,
            source_id="2015122300019902",
            title="[경기북부] 남양주왕숙2 A-3BL 공공분양주택 입주자 모집공고(기존임차인)",
            source_meta={"pan_id": "2015122300019902"},
            **common_fields,
        )

        profile = {**default_profile(), "preferred_regions": []}
        recommendation_ids = [item["notice_id"] for item in ranked_recommendations(profile, limit=20)]

        self.assertIn(987, recommendation_ids)
        self.assertNotIn(902, recommendation_ids)

    def test_recommendations_filter_out_unselected_regions(self):
        deadline = date.today() + timedelta(days=30)
        common_fields = {
            "provider": "LH",
            "supply_type": "공공분양",
            "housing_type": "분양주택",
            "area": "59.00",
            "price": 300000000,
            "contract_rate": 0.1,
            "application_deadline": deadline,
            "winner_date": deadline + timedelta(days=14),
            "contract_date": deadline + timedelta(days=30),
            "move_in": "2028-01",
            "competition": "100호",
            "source_url": "https://apply.lh.or.kr",
            "tags": ["LH", "공공분양"],
            "required_documents": [],
            "cautions": [],
            "ownership_type": "public_sale",
            "is_service_target": True,
        }
        HousingNotice.objects.create(
            id=981,
            source_id="SEOUL-REGION",
            title="서울 테스트 공공분양주택 입주자모집공고",
            region="서울",
            district="서울 테스트 단지",
            **common_fields,
        )
        HousingNotice.objects.create(
            id=982,
            source_id="CHUNGBUK-REGION",
            title="충북 테스트 공공분양주택 입주자모집공고",
            region="충청북도",
            district="충북 테스트 단지",
            **common_fields,
        )
        profile = {**default_profile(), "preferred_regions": ["서울", "경기 남부"]}

        recommendation_ids = [item["notice_id"] for item in ranked_recommendations(profile, limit=20)]

        self.assertIn(981, recommendation_ids)
        self.assertNotIn(982, recommendation_ids)

    def test_gyeonggi_subregion_filter_uses_title_when_lh_region_is_broad(self):
        deadline = date.today() + timedelta(days=30)
        HousingNotice.objects.create(
            id=983,
            source_id="GG-NORTH",
            title="[경기북부] 김포시 공공분양주택 입주자 모집공고",
            provider="LH",
            region="경기 남부",
            district="경기도",
            supply_type="공공분양",
            housing_type="분양주택",
            area="59.00",
            price=300000000,
            contract_rate=0.1,
            application_deadline=deadline,
            winner_date=deadline + timedelta(days=14),
            contract_date=deadline + timedelta(days=30),
            move_in="2028-01",
            competition="100호",
            source_url="https://apply.lh.or.kr",
            tags=["LH", "공공분양"],
            required_documents=[],
            cautions=[],
            ownership_type="public_sale",
            is_service_target=True,
        )
        south_profile = {**default_profile(), "preferred_regions": ["경기 남부"]}
        north_profile = {**default_profile(), "preferred_regions": ["경기 북부"]}

        south_ids = [item["notice_id"] for item in ranked_recommendations(south_profile, limit=20)]
        north_ids = [item["notice_id"] for item in ranked_recommendations(north_profile, limit=20)]

        self.assertNotIn(983, south_ids)
        self.assertIn(983, north_ids)

    def test_location_score_matches_region_alias_and_partial_supply_type(self):
        notice = {
            "region": "울산광역시",
            "district": "울산광역시",
            "supply_type": "신혼희망타운 공공분양",
            "housing_type": "공공분양주택",
        }
        profile = {
            "preferred_regions": ["울산"],
            "preferred_supply_types": ["공공분양", "신혼희망타운", "민간참여형 공공분양"],
        }

        self.assertEqual(location_score(notice, profile), 30)

    def test_location_score_gives_full_region_points_without_region_repeated_in_district(self):
        notice = {
            "region": "인천",
            "district": "서구 검단 AA21BL",
            "supply_type": "민간참여형 공공분양",
            "housing_type": "공공분양주택",
        }
        profile = {
            "preferred_regions": ["서울", "인천"],
            "preferred_supply_types": ["공공분양", "뉴홈", "신혼희망타운", "민간참여형 공공분양"],
        }

        self.assertEqual(location_score(notice, profile), 30)

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
        deadline = date.today() + timedelta(days=30)
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
            application_deadline=deadline,
            winner_date=deadline + timedelta(days=10),
            contract_date=deadline + timedelta(days=30),
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

        recommendation = next(
            item
            for item in ranked_recommendations(default_profile(), limit=20)
            if item["notice_id"] == 999
        )
        self.assertEqual(recommendation["best_option"]["option_id"], option.id)
        self.assertEqual(recommendation["top_options"][0]["option_id"], option.id)
        self.assertGreater(recommendation["best_option"]["option_fit_score"], 0)
        self.assertGreaterEqual(len(recommendation["best_option"]["fit_reasons"]), 1)

    def test_recommendations_prefer_general_supply_option_as_default(self):
        notice = HousingNotice.objects.create(
            id=996,
            source_id="LH-GENERAL-DEFAULT",
            title="일반공급 기본 선택 공공분양",
            provider="LH",
            region="서울",
            district="서울 테스트구",
            supply_type="공공분양",
            housing_type="분양주택",
            area="59m2",
            price=320000000,
            contract_rate=0.1,
            application_deadline="2026-07-01",
            winner_date="2026-07-10",
            contract_date="2026-08-01",
            move_in="2028-01",
            competition="100호",
            source_url="https://apply.lh.or.kr",
            tags=["LH", "공공분양"],
            required_documents=[],
            cautions=[],
            ownership_type="public_sale",
            is_service_target=True,
        )
        pre_option = HousingUnitOption.objects.create(
            notice=notice,
            unit_type="59A",
            exclusive_area_m2=59,
            floor_group="1층",
            option_type="pre_subscription",
            base_price=320000000,
            confidence=0.9,
        )
        general_option = HousingUnitOption.objects.create(
            notice=notice,
            unit_type="59A",
            exclusive_area_m2=59,
            floor_group="1층",
            option_type="general_supply",
            base_price=320000000,
            confidence=0.9,
        )
        for option in (pre_option, general_option):
            PaymentSchedule.objects.create(
                unit_option=option,
                label="계약금",
                amount=32000000,
                payment_type="down_payment",
                sequence=1,
            )

        recommendation = next(
            item
            for item in ranked_recommendations(default_profile(), limit=20)
            if item["notice_id"] == 996
        )

        self.assertEqual(recommendation["best_option"]["option_id"], general_option.id)
        self.assertEqual(recommendation["best_option"]["option_type"], "general_supply")

    @override_settings(FIRSTHOME_FIXTURE_FALLBACK={"ENABLE_SUPPLEMENT": True, "MIN_ACTIVE_SERVICE_NOTICES_PER_REGION": 5})
    def test_fixture_supplements_when_real_region_service_notices_are_too_few(self):
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
        gyeonggi_notices = [notice for notice in service_notices if "경기" in f"{notice['region']} {notice['district']}"]

        self.assertEqual(service_notices[0]["id"], 998)
        self.assertGreaterEqual(len(gyeonggi_notices), 5)
        self.assertTrue(any(notice["data_source"] == "fixture" for notice in gyeonggi_notices[1:]))
        self.assertTrue(all(notice["source_url"] == "" for notice in service_notices if notice["data_source"] == "fixture"))

    @override_settings(FIRSTHOME_FIXTURE_FALLBACK={"ENABLE_SUPPLEMENT": False, "MIN_ACTIVE_SERVICE_NOTICES_PER_REGION": 5})
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
