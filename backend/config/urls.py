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
from django.http import HttpResponse
from django.urls import path

from apps.ai_coach.views import coach_chat_view, coach_summary_view
from apps.notice_docs.views import (
    analyze_notice_document,
    notice_document_status,
    notice_eligibility_checklists,
    notice_unit_options,
)
from apps.notices.views import notice_detail, notice_list
from apps.profiles.views import auth_me_view, favorites_view, login_view, logout_view, profile_view, register_view
from apps.recommendations.views import (
    dashboard,
    funding_recommendation,
    housing_recommendations,
    policy_recommendations,
    product_recommendations,
)

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="bg" x1="10" x2="54" y1="8" y2="58" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#1D4ED8"/><stop offset=".55" stop-color="#0F766E"/><stop offset="1" stop-color="#F59E0B"/></linearGradient><linearGradient id="n" x1="21" x2="45" y1="47" y2="17" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FDE68A"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs><rect width="64" height="64" rx="14" fill="url(#bg)"/><circle cx="32" cy="32" r="21" fill="#FFFFFF" opacity=".16"/><path fill="#FFFFFF" d="M15.5 30.2 32 16.1l16.5 14.1-3.7 4.3-3.1-2.7v17.1H22.3V31.8l-3.1 2.7-3.7-4.3Z"/><path fill="#0F766E" d="M27 38.2c0-2.8 2.2-5 5-5s5 2.2 5 5v10.7H27V38.2Z"/><path fill="url(#n)" d="m43.7 18.9-6 22.1a2 2 0 0 1-1.4 1.4l-16 4.4 6.1-15.9a2 2 0 0 1 1.3-1.2l16-10.8Z"/><path fill="#1D4ED8" d="m32.1 31.4 4.2 4.2-9.7 4.4 5.5-8.6Z"/><circle cx="32" cy="32" r="3.2" fill="#FFFFFF"/></svg>"""


def favicon(_request):
    return HttpResponse(FAVICON_SVG, content_type="image/svg+xml")


urlpatterns = [
    path("favicon.ico", favicon),
    path('admin/', admin.site.urls),
    path("api/dashboard", dashboard),
    path("api/auth/me", auth_me_view),
    path("api/auth/register", register_view),
    path("api/auth/login", login_view),
    path("api/auth/logout", logout_view),
    path("api/profile", profile_view),
    path("api/favorites", favorites_view),
    path("api/recommendations/housing", housing_recommendations),
    path("api/recommendations/funding/<int:notice_id>", funding_recommendation),
    path("api/recommendations/products", product_recommendations),
    path("api/recommendations/policies", policy_recommendations),
    path("api/notices", notice_list),
    path("api/notices/<int:notice_id>", notice_detail),
    path("api/notices/<int:notice_id>/documents/status", notice_document_status),
    path("api/notices/<int:notice_id>/documents/analyze", analyze_notice_document),
    path("api/notices/<int:notice_id>/unit-options", notice_unit_options),
    path("api/notices/<int:notice_id>/eligibility-checklists", notice_eligibility_checklists),
    path("api/ai/coach-summary", coach_summary_view),
    path("api/ai/chat", coach_chat_view),
]
