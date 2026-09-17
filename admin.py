from django.contrib import admin
from .models import Biography, Work, Feedback


@admin.register(Biography)
class BiographyAdmin(admin.ModelAdmin):
    pass


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title",)
    list_filter = ("created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "short_message", "created_at")
    search_fields = ("name", "email", "message")
    list_filter = ("created_at",)
    list_per_page = 25

    def short_message(self, obj):
        # Admin ro‘yxatda xabar ham ko‘rinsin
        msg = (obj.message or "").strip()
        return (msg[:60] + "…") if len(msg) > 60 else msg

    short_message.short_description = "Xabar"
