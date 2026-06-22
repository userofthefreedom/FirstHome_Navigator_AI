from django.urls import path

from apps.community import views

urlpatterns = [
    path("agora/posts", views.posts_view),
    path("agora/posts/<int:post_id>", views.post_detail_view),
    path("agora/posts/<int:post_id>/comments", views.comments_view),
    path("agora/comments/<int:comment_id>", views.comment_detail_view),
]
