from django.urls import path

from apps.funding import views

app_name = "funding"

urlpatterns = [
    path("<int:notice_id>", views.funding_recommendation, name="recommendation"),
]
