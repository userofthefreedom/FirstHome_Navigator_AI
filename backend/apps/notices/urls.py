from django.urls import path

from apps.notices import views

app_name = "notices"

urlpatterns = [
    path("notices", views.notice_list, name="list"),
    path("notices/map", views.notice_map, name="map"),
    path("notices/<int:notice_id>", views.notice_detail, name="detail"),
]
