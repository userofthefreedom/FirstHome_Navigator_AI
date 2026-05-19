from django.test import SimpleTestCase

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
