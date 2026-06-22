from django.urls import path

from apps.products import views

urlpatterns = [
    path("products", views.products_view),
    path("products/joined", views.joined_products_view),
    path("products/<int:product_id>", views.product_detail_view),
    path("products/<int:product_id>/join", views.join_product_view),
]
