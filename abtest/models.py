from django.db import models

VARIANTS = ("kudos", "thanks")


class Impression(models.Model):
    """One row per visitor, created the first time they see the A/B page."""

    visitor_id = models.CharField(max_length=36, unique=True)
    variant = models.CharField(max_length=10, choices=[(v, v) for v in VARIANTS])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.visitor_id} saw {self.variant}"


class Click(models.Model):
    """At most one click per visitor: enforced by the one-to-one link to their impression."""

    impression = models.OneToOneField(Impression, on_delete=models.CASCADE, related_name="click")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.impression.visitor_id} clicked {self.impression.variant}"
