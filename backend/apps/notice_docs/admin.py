from django.contrib import admin

from apps.notice_docs.models import (
    EligibilityChecklist,
    ExtractionEvidence,
    HousingUnitOption,
    NoticeDocument,
    NoticeExtraction,
    PaymentSchedule,
)


admin.site.register(NoticeDocument)
admin.site.register(NoticeExtraction)
admin.site.register(HousingUnitOption)
admin.site.register(PaymentSchedule)
admin.site.register(EligibilityChecklist)
admin.site.register(ExtractionEvidence)
