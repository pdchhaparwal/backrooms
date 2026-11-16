from django.contrib import admin

from .models import Run


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "seconds", "distance", "attacks", "hits", "touched", "banished")
    list_filter = ("banished",)
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)
