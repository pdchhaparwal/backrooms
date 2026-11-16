from django.conf import settings
from django.db import models


class RadioMessage(models.Model):
    """One reply from the survival assistant ("the radio"): a hint plus a journal entry.

    Stored so we can show history later, audit what the model said, and enforce a
    per-player daily limit.
    """

    SOURCE_LLM = "llm"
    SOURCE_FALLBACK = "fallback"
    SOURCES = ((SOURCE_LLM, "LLM via OpenRouter"), (SOURCE_FALLBACK, "Built-in rules"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="radio_messages")
    run = models.ForeignKey("game.Run", null=True, blank=True, on_delete=models.SET_NULL, related_name="radio_messages")
    phase = models.CharField(max_length=10)  # "running" (mid-run hint) or "ended" (after a run)
    situation = models.JSONField(help_text="The validated game state the hint was based on")
    hint = models.CharField(max_length=300)
    journal = models.CharField(max_length=400)
    source = models.CharField(max_length=10, choices=SOURCES)
    model = models.CharField(max_length=100, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=200, blank=True, help_text="Why we fell back, if we did")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"], name="radio_user_day")]

    def __str__(self):
        return f"{self.user} · {self.phase} · {self.source}"
