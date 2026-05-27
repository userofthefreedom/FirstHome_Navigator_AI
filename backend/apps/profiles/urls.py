from django.urls import path

from apps.profiles import views

app_name = "profiles"

urlpatterns = [
    path("auth/me", views.auth_me_view, name="auth_me"),
    path("auth/register", views.register_view, name="register"),
    path("auth/login", views.login_view, name="login"),
    path("auth/logout", views.logout_view, name="logout"),
    path("profile", views.profile_view, name="profile"),
    path("favorites", views.favorites_view, name="favorites"),
]
