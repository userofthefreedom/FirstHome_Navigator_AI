from django.urls import path

from apps.recommendations import views

app_name = "recommendations"

urlpatterns = [
    path("dashboard", views.dashboard, name="dashboard"),
    path("recommendations/housing", views.housing_recommendations, name="housing"),
    path("recommendations/products", views.product_recommendations, name="products"),
    path("recommendations/loans", views.loan_recommendations, name="loans"),
    path("recommendations/policies", views.policy_recommendations, name="policies"),
]
