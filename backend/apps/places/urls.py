from django.urls import path

from apps.places import views

urlpatterns = [
    path("places/search", views.search_places_view),
    path("places/route", views.route_view),
]
