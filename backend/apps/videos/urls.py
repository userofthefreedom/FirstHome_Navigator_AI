from django.urls import path

from apps.videos import views

urlpatterns = [
    path("videos/default", views.default_videos_view),
    path("videos/search", views.search_videos_view),
]
