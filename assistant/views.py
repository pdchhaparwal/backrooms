import json
import logging
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from game.models import Run

from . import llm
from .forms import SituationForm
from .models import RadioMessage

logger = logging.getLogger(__name__)


def used_today(user):
    return RadioMessage.objects.filter(user=user, created_at__gte=timezone.now() - timedelta(hours=24)).count()


@require_POST
def radio(request):
    """POST /assistant/radio/ with the game situation -> {"hint", "journal", "source", "remaining"}."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login required"}, status=401)
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "expected a JSON object"}, status=400)
    form = SituationForm(payload)
    if not form.is_valid():
        return JsonResponse({"error": "invalid situation", "fields": form.errors}, status=400)

    limit = settings.ASSISTANT_DAILY_LIMIT
    used = used_today(request.user)
    if used >= limit:
        return JsonResponse(
            {"error": "daily limit reached", "hint": "The radio is silent. It has said enough for today.", "remaining": 0},
            status=429,
        )

    situation = {k: v for k, v in form.cleaned_data.items() if k != "run_id"}
    run = None
    if form.cleaned_data.get("run_id"):
        run = Run.objects.filter(pk=form.cleaned_data["run_id"], user=request.user).first()  # only your own runs

    reply = llm.ask_radio(situation)
    RadioMessage.objects.create(
        user=request.user, run=run, phase=situation["phase"], situation=situation,
        hint=reply.hint, journal=reply.journal, source=reply.source, model=reply.model,
        latency_ms=reply.latency_ms, error=reply.error,
    )
    if reply.error:
        logger.info("radio fallback for user=%s: %s", request.user.pk, reply.error)
    return JsonResponse(
        {"hint": reply.hint, "journal": reply.journal, "source": reply.source, "remaining": limit - used - 1}
    )
