from django.contrib import admin

from .models import RadioMessage


@admin.register(RadioMessage)
class RadioMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "phase", "source", "model", "latency_ms", "hint")
    list_filter = ("source", "phase", "model")
    search_fields = ("user__username", "hint", "journal")
    readonly_fields = [f.name for f in RadioMessage._meta.fields]
