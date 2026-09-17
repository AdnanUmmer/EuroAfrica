from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "receive_offers", "google_account", "updated_at")
    list_filter = ("receive_offers", "google_account")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone_number")

