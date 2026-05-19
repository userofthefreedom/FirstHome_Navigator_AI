from django.contrib import admin

from apps.profiles.models import Favorite, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "birth_year", "annual_income", "asset", "monthly_saving", "updated_at")
    search_fields = ("name",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "favorite_type", "object_id", "created_at")
    list_filter = ("favorite_type",)
