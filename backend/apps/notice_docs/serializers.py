from __future__ import annotations

from apps.notice_docs.models import EligibilityChecklist, HousingUnitOption, NoticeDocument, PaymentSchedule


def serialize_document(document: NoticeDocument) -> dict:
    return {
        "id": document.id,
        "notice_id": document.notice_id,
        "provider": document.provider,
        "file_id": document.file_id,
        "file_name": document.file_name,
        "document_url": document.document_url,
        "source_url": document.source_url,
        "status": document.status,
        "error_message": document.error_message,
        "fetched_at": document.fetched_at.isoformat() if document.fetched_at else "",
        "analyzed_at": document.analyzed_at.isoformat() if document.analyzed_at else "",
    }


def serialize_payment_schedule(schedule: PaymentSchedule) -> dict:
    return {
        "id": schedule.id,
        "label": schedule.label,
        "due_date": schedule.due_date.isoformat() if schedule.due_date else "",
        "amount": schedule.amount,
        "payment_type": schedule.payment_type,
        "sequence": schedule.sequence,
        "evidence_text": schedule.evidence_text,
    }


def serialize_unit_option(option: HousingUnitOption) -> dict:
    return {
        "id": option.id,
        "notice_id": option.notice_id,
        "document_id": option.document_id,
        "unit_type": option.unit_type,
        "exclusive_area_m2": option.exclusive_area_m2,
        "floor_group": option.floor_group,
        "option_type": option.option_type,
        "base_price": option.base_price,
        "loan_amount": option.loan_amount,
        "balcony_extension_price": option.balcony_extension_price,
        "confidence": option.confidence,
        "source_page": option.source_page,
        "source_text": option.source_text,
        "payment_schedules": [
            serialize_payment_schedule(schedule)
            for schedule in option.payment_schedules.all()
        ],
    }


def serialize_checklist(item: EligibilityChecklist) -> dict:
    return {
        "id": item.id,
        "notice_id": item.notice_id,
        "document_id": item.document_id,
        "category": item.category,
        "title": item.title,
        "condition_text": item.condition_text,
        "evidence_text": item.evidence_text,
        "confidence": item.confidence,
    }
