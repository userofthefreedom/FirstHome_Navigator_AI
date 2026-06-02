from __future__ import annotations


NOTICE_DOCUMENT_EXTRACTION_SCHEMA = {
    "name": "firsthome_notice_document_extraction",
    "description": "공공분양 공고문에서 주택형 옵션, 납부 일정, 자격 확인 항목을 구조화한다.",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "unit_options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "unit_type": {"type": "string"},
                        "exclusive_area_m2": {"type": "number"},
                        "floor_group": {"type": "string"},
                        "option_type": {
                            "type": "string",
                            "enum": ["basic", "general_supply", "pre_subscription", "minus", "other"],
                        },
                        "base_price": {"type": "integer"},
                        "loan_amount": {"type": "integer"},
                        "balcony_extension_price": {"type": "integer"},
                        "confidence": {"type": "number"},
                        "source_page": {"type": "integer"},
                        "source_text": {"type": "string"},
                        "payment_schedules": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "label": {"type": "string"},
                                    "due_date": {"type": "string"},
                                    "amount": {"type": "integer"},
                                    "payment_type": {
                                        "type": "string",
                                        "enum": [
                                            "application",
                                            "winner",
                                            "down_payment",
                                            "middle_payment",
                                            "final_payment",
                                            "installment_payment",
                                            "move_in_balance",
                                            "other",
                                        ],
                                    },
                                    "sequence": {"type": "integer"},
                                    "evidence_text": {"type": "string"},
                                },
                                "required": ["label", "due_date", "amount", "payment_type", "sequence", "evidence_text"],
                            },
                        },
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "field_path": {"type": "string"},
                                    "page_no": {"type": "integer"},
                                    "source_text": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": ["field_path", "page_no", "source_text", "confidence"],
                            },
                        },
                    },
                    "required": [
                        "unit_type",
                        "exclusive_area_m2",
                        "floor_group",
                        "option_type",
                        "base_price",
                        "loan_amount",
                        "balcony_extension_price",
                        "confidence",
                        "source_page",
                        "source_text",
                        "payment_schedules",
                        "evidence",
                    ],
                },
            },
            "eligibility_checklists": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string"},
                        "title": {"type": "string"},
                        "condition_text": {"type": "string"},
                        "evidence_text": {"type": "string"},
                        "page_no": {"type": "integer"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["category", "title", "condition_text", "evidence_text", "page_no", "confidence"],
                },
            },
            "required_documents": {
                "type": "array",
                "items": {"type": "string"},
            },
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["unit_options", "eligibility_checklists", "required_documents", "warnings"],
    },
}


COACH_CHAT_SCHEMA = {
    "name": "firsthome_coach_chat",
    "description": "사용자의 공공분양 준비 질문에 참고 답변과 실행 항목을 제공한다.",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reply": {"type": "string"},
            "suggested_actions": {"type": "array", "items": {"type": "string"}},
            "context_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string"},
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                    },
                    "required": ["type", "id", "label"],
                },
            },
        },
        "required": ["reply", "suggested_actions", "context_refs"],
    },
}
