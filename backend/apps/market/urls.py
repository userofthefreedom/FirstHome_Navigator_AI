from django.urls import path

from apps.market import views

urlpatterns = [
    path("market/assets", views.market_assets_view),
    path("market/summary", views.market_summary_view),
]
