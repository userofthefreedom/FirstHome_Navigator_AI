from django.conf import settings
from django.db import models


class AgoraPost(models.Model):
    CATEGORY_CHOICES = [
        ("notice", "청약"),
        ("product", "금융상품"),
        ("funding", "자금준비"),
        ("free", "자유"),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="agora_posts", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    content = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="free")
    related_notice_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return self.title


class AgoraComment(models.Model):
    post = models.ForeignKey(AgoraPost, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="agora_comments", on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.post_id}:{self.author_id}"
