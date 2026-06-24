from django.test import SimpleTestCase

from apps.rules.matching import policy_match_score
from apps.policies.services.youthcenter import normalize_youthcenter_policies


class YouthCenterPolicyNormalizerTests(SimpleTestCase):
    def test_json_policy_is_normalized(self):
        payload = {
            "result": {
                "youthPolicyList": [
                    {
                        "plcyNm": "청년 주거비 지원",
                        "sprvsnInstCdNm": "서울시",
                        "sprtTrgtCn": "19세 ~ 34세 무주택 청년",
                        "plcySprtCn": "월세 20만원 지원",
                        "lclsfNm": "주거",
                        "aplyUrlAddr": "https://www.youthcenter.go.kr/policy",
                    }
                ]
            }
        }

        policies = normalize_youthcenter_policies(payload)

        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0].name, "청년 주거비 지원")
        self.assertEqual(policies[0].provider, "서울시")
        self.assertEqual(policies[0].policy_category, "주거")
        self.assertEqual(policies[0].regions, ["서울"])
        self.assertEqual(policies[0].age_min, 19)
        self.assertEqual(policies[0].age_max, 34)
        self.assertTrue(policies[0].requires_homeless)

    def test_xml_policy_is_normalized(self):
        payload = {
            "youthPolicyList": [
                {
                    "polyBizSjnm": "청년 자산형성",
                    "cnsgNmor": "고용노동부",
                    "ageInfo": "만 19세 이상 39세 이하",
                    "sporCn": "저축 장려금 지원",
                    "bizTycdNm": "금융",
                }
            ]
        }

        policies = normalize_youthcenter_policies(payload)

        self.assertEqual(policies[0].name, "청년 자산형성")
        self.assertEqual(policies[0].provider, "고용노동부")
        self.assertEqual(policies[0].regions, ["전국"])
        self.assertEqual(policies[0].age_min, 19)
        self.assertEqual(policies[0].age_max, 39)

    def test_full_province_name_is_normalized_to_region_alias(self):
        payload = {
            "youthPolicyList": [
                {
                    "plcyNm": "2026년 청년 전월세 보증금 지원",
                    "sprvsnInstCdNm": "경상북도 고령군",
                    "sprtTrgtCn": "경상북도 고령군 거주 무주택 청년",
                    "plcySprtCn": "전월세 보증금 이자 지원",
                    "lclsfNm": "주거",
                }
            ]
        }

        policies = normalize_youthcenter_policies(payload)

        self.assertEqual(policies[0].regions, ["경북"])


class PolicyMatchScoreTests(SimpleTestCase):
    def test_region_mismatch_returns_zero_score(self):
        profile = {
            "birth_year": 1999,
            "annual_income": 50000000,
            "preferred_regions": ["인천"],
            "is_homeless": True,
        }
        policy = {
            "name": "태안 청년 신혼부부 주택자금 대출이자 지원",
            "provider": "태안군",
            "target": "태안군 거주 청년",
            "benefit": "가구당 대출이자 지원",
            "policy_category": "주거",
            "regions": ["충남"],
            "age_min": 19,
            "age_max": 39,
            "requires_homeless": True,
            "source_url": "https://example.com/policy",
        }

        score, source_priority = policy_match_score(policy, profile)

        self.assertEqual(score, 0)
        self.assertEqual(source_priority, 0)

    def test_matching_housing_policy_uses_expanded_score_scale(self):
        profile = {
            "birth_year": 1999,
            "annual_income": 50000000,
            "preferred_regions": ["인천"],
            "is_homeless": True,
        }
        policy = {
            "name": "인천 청년 공공분양 청약 상담",
            "provider": "인천광역시",
            "target": "인천 무주택 청년",
            "benefit": "청약 자격과 주택구입 자금 상담",
            "policy_category": "주거",
            "regions": ["인천"],
            "age_min": 19,
            "age_max": 39,
            "max_income": 70000000,
            "requires_homeless": True,
            "source_url": "https://example.com/policy",
        }

        score, _ = policy_match_score(policy, profile)

        self.assertGreaterEqual(score, 90)
