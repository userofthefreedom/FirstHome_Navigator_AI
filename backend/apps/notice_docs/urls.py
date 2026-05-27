from django.urls import path

from apps.notice_docs import views

app_name = "notice_docs"

urlpatterns = [
    path("documents/status", views.notice_document_status, name="status"),
    path("documents/analyze", views.analyze_notice_document, name="analyze"),
    path("unit-options", views.notice_unit_options, name="unit_options"),
    path("eligibility-checklists", views.notice_eligibility_checklists, name="eligibility_checklists"),
]
