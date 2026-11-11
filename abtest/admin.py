from django.contrib import admin

from .models import Click, Impression


@admin.register(Impression)
class ImpressionAdmin(admin.ModelAdmin):
    list_display = ("visitor_id", "variant", "created_at")
    list_filter = ("variant",)


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ("impression", "created_at")
