from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "is_active", "starts_at", "ends_at", "emailed_at")
    list_filter = ("level", "is_active")
    search_fields = ("title", "body")
