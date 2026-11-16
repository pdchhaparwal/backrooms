from django.conf import settings
from django.db import models


class Run(models.Model):
    """One finished run of Level 0 by a logged-in player."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="runs")
    seconds = models.FloatField(help_text="Time survived, in seconds")
    distance = models.FloatField(help_text="Tiles walked")
    attacks = models.PositiveIntegerField(default=0)
    hits = models.PositiveIntegerField(default=0)
    touched = models.PositiveIntegerField(default=0, help_text="Times the entity touched the player")
    banished = models.BooleanField(default=False, help_text="Entity banished during the run")
    created_at = models.DateTimeField(auto_now_add=True)

    # "Best" = banished the entity first, then walked the furthest, then the earliest such run.
    BEST_ORDER = ("-banished", "-distance", "created_at")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="run_user_recent")]

    def __str__(self):
        return f"{self.user} · {self.distance:.1f} tiles · {'banished' if self.banished else 'survived'}"

    @classmethod
    def best_for(cls, user):
        return cls.objects.filter(user=user).order_by(*cls.BEST_ORDER).first()


class PlayNowView(models.Model):
    """Play Now page experiment: one row per session, recording the design it first saw."""

    VARIANTS = (("a", "A · Level 0"), ("b", "B · Found footage"))

    visitor_id = models.CharField(max_length=36, unique=True)
    variant = models.CharField(max_length=1, choices=VARIANTS)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.visitor_id} saw Play Now {self.variant.upper()}"


class PlayNowStart(models.Model):
    """Conversion: that session went on to start a run. At most one per view."""

    view = models.OneToOneField(PlayNowView, on_delete=models.CASCADE, related_name="start")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.view.visitor_id} started a run (variant {self.view.variant.upper()})"
