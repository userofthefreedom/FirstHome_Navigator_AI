from django.urls import path

from apps.ai_coach import views

app_name = "ai_coach"

urlpatterns = [
    path("coach-summary", views.coach_summary_view, name="summary"),
    path("coach-summary/latest", views.latest_coach_summary_view, name="summary_latest"),
    path("chat", views.coach_chat_view, name="chat"),
]
