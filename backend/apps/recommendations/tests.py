from datetime import date, timedelta

from django.test import SimpleTestCase, TestCase, override_settings

from apps.fixture_store import current_notices, default_profile, find_notice, load_fixture, notices, seed_fixture_notice_analysis, sync_fixture_supplements
from apps.funding.services.calculator import funding_plan
from apps.notice_docs.models import HousingUnitOption, PaymentSchedule
from apps.notices.models import HousingNotice
from apps.policies.models import YouthPolicy
from apps.policies.services.matcher import match_policies
from apps.products.models import FinancialProduct, LoanProduct
from apps.products.services.loan_matcher import match_purchase_loans
from apps.products.services.matcher import match_products
from apps.recommendations.services.ranking import ranked_recommendations
from apps.rules.confidence import option_confidence_from_quality
from apps.rules.funding import (
    available_cash,
    ceil_divide,
    default_payment_amounts,
    effective_down_payment_cash,
    effective_monthly_capacity,
)
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

    def test_debt_and_job_status_adjust_funding_capacity(self):
        profile = {
            "asset": 50_000_000,
            "debt": 12_000_000,
            "monthly_payment_capacity": 1_200_000,
            "job_status": "unemployed",
        }

        self.assertEqual(available_cash(profile), 46_400_000)
        self.assertEqual(effective_down_payment_cash(profile), 46_400_000)
        self.assertEqual(effective_monthly_capacity(profile), 820_000)

    def test_option_price_and_area_scores_decline_by_gap_ratio(self):
        profile = {
            "desired_area_min_m2": 50,
            "desired_area_max_m2": 60,
            "desired_price_min": 300_000_000,
            "desired_price_max": 500_000_000,
            "max_down_payment": 60_000_000,
            "monthly_payment_capacity": 10_000_000,
        }
        in_range = {
            "exclusive_area_m2": 59,
            "base_price": 500_000_000,
            "down_payment": 50_000_000,
            "middle_payment": 100_000_000,
        }
        slightly_over = {
            **in_range,
            "exclusive_area_m2": 63,
            "base_price": 525_000_000,
        }
        far_over = {
            **in_range,
            "exclusive_area_m2": 84,
            "base_price": 700_000_000,
        }

        self.assertGreater(option_fit_score(in_range, profile), option_fit_score(slightly_over, profile))
        self.assertGreater(option_fit_score(slightly_over, profile), option_fit_score(far_over, profile))

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
        self.assertEqual(plan["available_cash"], 7100000)
        self.assertEqual(plan["shortfall"], 44900000)
        self.assertEqual(plan["monthly_target"], 2494445)

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
        fixture_data = load_fixture()
        self.assertGreaterEqual(len(fixture_data["loan_products"]), 40)
        self.assertGreaterEqual(len(fixture_data["policies"]), 100)
        self.assertGreaterEqual(len(match_products(default_profile(), limit=20)), 8)
        self.assertGreaterEqual(len(match_policies(default_profile(), limit=20)), 8)
        self.assertGreaterEqual(len(match_purchase_loans(default_profile(), limit=20)), 8)

    def test_fixture_analysis_seed_is_idempotent(self):
        fixture_notice = load_fixture()["notices"][0]
        sync_fixture_supplements(min_per_region=5)
        notice = HousingNotice.objects.get(id=int(fixture_notice["id"]))

        seed_fixture_notice_analysis(notice, fixture_notice)
        first_option_count = HousingUnitOption.objects.filter(notice=notice).count()
        first_schedule_count = PaymentSchedule.objects.filter(unit_option__notice=notice).count()

        seed_fixture_notice_analysis(notice, fixture_notice)

        self.assertEqual(HousingUnitOption.objects.filter(notice=notice).count(), first_option_count)
        self.assertEqual(PaymentSchedule.objects.filter(unit_option__notice=notice).count(), first_schedule_count)

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

    def test_fixture_funding_score_keeps_user_cash_signal(self):
        profile = {
            **default_profile(),
            "annual_income": 50_000_000,
            "asset": 10_000_000,
            "debt": 3_000_000,
            "monthly_saving": 1_000_000,
            "desired_price_min": 200_000_000,
            "desired_price_max": 555_000_000,
            "max_down_payment": 50_000_000,
            "monthly_payment_capacity": 1_200_000,
            "desired_area_min_m2": 48,
            "desired_area_max_m2": 84,
            "preferred_regions": ["인천"],
            "preferred_supply_types": ["공공분양", "뉴홈", "신혼희망타운", "민간참여형 공공분양"],
        }

        recommendations = ranked_recommendations(profile, limit=6)

        self.assertTrue(recommendations)
        self.assertTrue(any(item["score_detail"]["funding"] > 0 for item in recommendations))

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

    def test_policy_matcher_excludes_unrelated_policy_categories(self):
        YouthPolicy.objects.create(
            id=9101,
            name="청년 문화활동 바우처",
            provider="테스트기관",
            target="청년",
            benefit="공연 관람비 지원",
            policy_category="문화",
            regions=["전국"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=False,
            source_url="https://example.com/culture",
            reasons=["비주거 정책입니다."],
        )
        YouthPolicy.objects.create(
            id=9102,
            name="청년 전월세 보증금 이자 지원",
            provider="테스트기관",
            target="무주택 청년",
            benefit="전월세 보증금 대출이자 일부 지원",
            policy_category="전세",
            regions=["전국"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=True,
            source_url="https://example.com/housing",
            reasons=["주거 정책입니다."],
        )

        policy_ids = [policy["id"] for policy in match_policies(default_profile(), limit=20)]

        self.assertIn(9102, policy_ids)
        self.assertNotIn(9101, policy_ids)

    def test_policy_matcher_excludes_unselected_local_regions(self):
        YouthPolicy.objects.create(
            id=9111,
            name="강화 청년 전세보증금 지원",
            provider="인천광역시",
            target="인천 청년",
            benefit="전세보증금 이자 지원",
            policy_category="전세",
            regions=["인천"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=True,
            source_url="https://example.com/incheon",
            reasons=["인천 지역 정책입니다."],
        )
        YouthPolicy.objects.create(
            id=9112,
            name="전국 청년 주거자금 상담",
            provider="국토교통부",
            target="무주택 청년",
            benefit="주거자금 상담",
            policy_category="주거지원",
            regions=["전국"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=True,
            source_url="https://example.com/nationwide",
            reasons=["전국 정책입니다."],
        )
        profile = {**default_profile(), "preferred_regions": ["부산"]}

        policy_ids = [policy["id"] for policy in match_policies(profile, limit=30)]

        self.assertIn(9112, policy_ids)
        self.assertNotIn(9111, policy_ids)

    def test_policy_matcher_infers_local_policy_region_before_nationwide_fallback(self):
        YouthPolicy.objects.create(
            id=9113,
            name="태안 청년 신혼부부 주택자금 대출이자 지원",
            provider="신속허가과",
            target="태안 청년 신혼부부",
            benefit="가구당 연간 100만원 이내 대출이자 지원",
            policy_category="주거",
            regions=["전국"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=True,
            source_url="https://example.com/taean",
            reasons=["저장 지역이 전국이어도 정책명으로 실제 지역을 추론합니다."],
        )
        incheon_profile = {**default_profile(), "preferred_regions": ["인천"]}
        chungnam_profile = {**default_profile(), "preferred_regions": ["충남"]}

        incheon_policy_ids = [policy["id"] for policy in match_policies(incheon_profile, limit=30)]
        chungnam_policy_ids = [policy["id"] for policy in match_policies(chungnam_profile, limit=30)]

        self.assertNotIn(9113, incheon_policy_ids)
        self.assertIn(9113, chungnam_policy_ids)

    def test_policy_matcher_excludes_business_rent_support(self):
        YouthPolicy.objects.create(
            id=9121,
            name="2026년 청년창업자 임차료 지원사업",
            provider="경상북도 고령군 인구정책실",
            target="고령군 거주 예정 초기 청년창업가",
            benefit="사업장 임차료 일부 지원",
            policy_category="일자리",
            regions=["전국"],
            age_min=18,
            age_max=45,
            max_income=0,
            requires_homeless=False,
            source_url="https://example.com/startup-rent",
            reasons=["창업 정책입니다."],
        )
        profile = {**default_profile(), "preferred_regions": ["서울", "경기 남부", "경기 북부", "인천"]}

        policy_ids = [policy["id"] for policy in match_policies(profile, limit=30)]

        self.assertNotIn(9121, policy_ids)

    def test_policy_matcher_excludes_non_housing_fund_jobs(self):
        YouthPolicy.objects.create(
            id=9131,
            name="청년어업인 영어정착지원",
            provider="인천광역시 수산기술지원센터",
            target="인천 청년 어업인",
            benefit="정착 지원금과 창업 자금을 지원합니다.",
            policy_category="일자리",
            regions=["인천"],
            age_min=18,
            age_max=45,
            max_income=0,
            requires_homeless=False,
            source_url="https://example.com/fishery",
            reasons=["일자리 정책입니다."],
        )
        YouthPolicy.objects.create(
            id=9132,
            name="인천 청년 주거자금 상담",
            provider="인천광역시",
            target="인천 무주택 청년",
            benefit="청약과 주거자금 상담을 지원합니다.",
            policy_category="주거지원",
            regions=["인천"],
            age_min=19,
            age_max=39,
            max_income=0,
            requires_homeless=True,
            source_url="https://example.com/incheon-housing",
            reasons=["주거 정책입니다."],
        )
        profile = {**default_profile(), "preferred_regions": ["인천"]}

        policy_ids = [policy["id"] for policy in match_policies(profile, limit=30)]

        self.assertIn(9132, policy_ids)
        self.assertNotIn(9131, policy_ids)

    def test_purchase_loan_matcher_only_keeps_home_purchase_loans(self):
        profile = {
            **default_profile(),
            "birth_year": 1996,
            "annual_income": 50_000_000,
            "asset": 10_000_000,
            "is_homeless": True,
            "monthly_payment_capacity": 1_200_000,
        }
        plan = {
            "price": 500_000_000,
            "exclusive_area_m2": 59,
            "shortfall": 40_000_000,
            "available_cash": 10_000_000,
            "timeline_summary": {"due_before_move_in": 300_000_000},
        }
        candidates = [
            {
                "id": 1,
                "name": "생애최초 주택구입자금",
                "provider": "테스트",
                "category": "구입자금 대출",
                "loan_purpose": "first_home_purchase",
                "limit_amount": 300_000_000,
                "term_years": 30,
                "age_min": 19,
                "age_max": 70,
                "max_income": 70_000_000,
                "max_price": 600_000_000,
                "max_area_m2": 85,
                "requires_homeless": True,
                "source_url": "https://example.com/purchase",
            },
            {
                "id": 2,
                "name": "청년 전세자금대출",
                "provider": "테스트",
                "category": "전세자금",
                "loan_purpose": "jeonse",
            },
            {
                "id": 3,
                "name": "주택청약통장담보대출",
                "provider": "테스트",
                "category": "담보대출",
                "loan_purpose": "subscription_collateral",
            },
        ]

        matched = match_purchase_loans(profile, plan, candidates=candidates)

        self.assertEqual([loan["id"] for loan in matched], [1])
        self.assertGreater(matched[0]["match_score"], 0)

    def test_purchase_loan_matcher_dedupes_same_provider_product_options(self):
        profile = {**default_profile(), "is_homeless": True}
        plan = {
            "price": 500_000_000,
            "exclusive_area_m2": 59,
            "shortfall": 40_000_000,
            "available_cash": 10_000_000,
            "timeline_summary": {"due_before_move_in": 300_000_000},
        }
        common = {
            "category": "주택담보대출",
            "loan_purpose": "purchase",
            "limit_amount": 400_000_000,
            "term_years": 30,
            "age_min": 19,
            "age_max": 70,
            "source_url": "https://finlife.fss.or.kr/finlife/main/contents.do?menuNo=700029",
        }
        candidates = [
            {**common, "id": 1, "provider": "테스트은행", "name": "주택담보대출 (아파트 · 고정금리)"},
            {**common, "id": 2, "provider": "테스트은행", "name": "주택담보대출 (아파트 · 변동금리)"},
            {**common, "id": 3, "provider": "다른은행", "name": "내집마련대출 (아파트 · 고정금리)"},
        ]

        matched = match_purchase_loans(profile, plan, candidates=candidates, limit=2)

        self.assertEqual([loan["id"] for loan in matched], [1, 3])

    def test_db_purchase_loans_are_used_before_fixture_supplements(self):
        LoanProduct.objects.create(
            id=999,
            name="DB 생애최초 구입자금",
            provider="테스트은행",
            category="주택담보대출",
            loan_purpose="purchase",
            description="DB에서 수집한 주택 구입 목적 대출입니다.",
            target="주택 구입 예정자",
            rate="최저 연 3.20%",
            limit="최대 4억원",
            limit_amount=400000000,
            term="최대 30년",
            term_years=30,
            age_min=19,
            age_max=70,
            max_income=0,
            max_price=0,
            max_area_m2=0,
            requires_homeless=False,
            source_url="https://finlife.fss.or.kr/finlife/main/contents.do?menuNo=700029",
            reasons=["금융감독원 API 수집 상품입니다."],
            caveats=["공식 심사가 필요합니다."],
        )

        matched = match_purchase_loans(default_profile(), limit=5)

        self.assertTrue(matched)
        self.assertEqual(matched[0]["id"], 999)
        self.assertEqual(matched[0]["data_source"], "금융감독원 API")

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
            target="무주택 청년",
            benefit="청약 및 주거 상담",
            policy_category="주거",
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

        sync_fixture_supplements(min_per_region=5)
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
