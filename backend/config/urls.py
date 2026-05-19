"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from apps.ai_coach.views import coach_summary_view
from apps.notices.views import notice_detail, notice_list
from apps.profiles.views import favorites_view, profile_view
from apps.recommendations.views import (
    dashboard,
    funding_recommendation,
    housing_recommendations,
    policy_recommendations,
    product_recommendations,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/dashboard", dashboard),
    path("api/profile", profile_view),
    path("api/favorites", favorites_view),
    path("api/recommendations/housing", housing_recommendations),
    path("api/recommendations/funding/<int:notice_id>", funding_recommendation),
    path("api/recommendations/products", product_recommendations),
    path("api/recommendations/policies", policy_recommendations),
    path("api/notices", notice_list),
    path("api/notices/<int:notice_id>", notice_detail),
    path("api/ai/coach-summary", coach_summary_view),
]
