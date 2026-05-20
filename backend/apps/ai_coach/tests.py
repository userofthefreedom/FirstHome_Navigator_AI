from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.ai_coach.models import AiExtractionResult


class AiExtractionResultTests(TestCase):
    def test_extraction_result_stores_structured_fields(self):
        result = AiExtractionResult.objects.create(
            source_type="notice",
            source_id=101,
            source_title="서울 청년 행복주택",
            source_url="https://example.com/notice/101",
            extraction_type="housing_notice",
            model_name="gpt-test",
            input_hash="a" * 64,
        )

        result.mark_succeeded(
            extracted_data={"deposit": 12000000, "monthly_rent": 180000},
            confidence={"deposit": 0.92, "monthly_rent": 0.87},
            missing_fields=["income_limit"],
            warnings=["income limit was not present in the source text"],
            raw_response={"id": "response-test"},
        )

        result.refresh_from_db()
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.extracted_data["deposit"], 12000000)
        self.assertEqual(result.confidence["deposit"], 0.92)
        self.assertEqual(result.missing_fields, ["income_limit"])
        self.assertEqual(result.error_message, "")

    def test_extraction_result_can_record_failure(self):
        result = AiExtractionResult.objects.create(
            source_type="policy",
            source_id=301,
            source_title="청년 월세 지원",
            extraction_type="youth_policy",
        )

        result.mark_failed("source document could not be parsed", raw_response={"status": 422})

        result.refresh_from_db()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_message, "source document could not be parsed")
        self.assertEqual(result.raw_response["status"], 422)

    def test_same_source_and_input_hash_is_unique(self):
        payload = {
            "source_type": "notice",
            "source_id": 101,
            "extraction_type": "housing_notice",
            "input_hash": "b" * 64,
        }
        AiExtractionResult.objects.create(**payload)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AiExtractionResult.objects.create(**payload)
