from django.contrib import admin

from .models import PlayNowStart, PlayNowView, Run


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "seconds", "distance", "attacks", "hits", "touched", "banished")
    list_filter = ("banished",)
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)


@admin.register(PlayNowView)
class PlayNowViewAdmin(admin.ModelAdmin):
    list_display = ("visitor_id", "variant", "user", "created_at")
    list_filter = ("variant",)


@admin.register(PlayNowStart)
class PlayNowStartAdmin(admin.ModelAdmin):
    list_display = ("view", "created_at")
    list_filter = ("view__variant",)
