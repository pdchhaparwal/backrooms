import json
import logging

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import variants
from .forms import RunForm
from .models import Run

logger = logging.getLogger(__name__)


class VariantLoginView(LoginView):
    redirect_authenticated_user = True

    def get_template_names(self):
        self.variant = variants.pick(self.request, "login")
        return [f"registration/login_{self.variant}.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(variants.context(variants.pick(self.request, "login")))
        return ctx


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    ctx = {"form": form, **variants.context(variants.pick(request, "login"))}
    return render(request, "registration/signup.html", ctx)


@login_required
def home(request):
    """The 'Play Now' page."""
    v = variants.pick(request, "home")
    ctx = {
        **variants.context(v),
        "recent_runs": Run.objects.filter(user=request.user)[:5],
        "best_run": Run.best_for(request.user),
    }
    return render(request, f"game/home_{v}.html", ctx)


@login_required
def instructions(request):
    v = variants.pick(request, "instructions")
    ctx = {**variants.context(v), "demo_seconds": settings.DEMO_SECONDS}
    return render(request, f"game/instructions_{v}.html", ctx)


@login_required
def play(request):
    try:
        seconds = max(1, min(600, int(request.GET.get("t", settings.DEMO_SECONDS))))
    except ValueError:
        seconds = settings.DEMO_SECONDS
    return render(request, "game/play.html", {"demo_seconds": seconds, "theme": "theme-play"})


@require_POST
def save_run(request):
    """Save the stats of a finished run for the logged-in player (JSON in, JSON out)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login required"}, status=401)
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "expected a JSON object"}, status=400)
    form = RunForm(payload)
    if not form.is_valid():
        return JsonResponse({"error": "invalid run", "fields": form.errors}, status=400)
    previous_best = Run.best_for(request.user)
    run = form.save(commit=False)
    run.user = request.user  # always the session user, never a value from the request
    run.save()
    is_best = Run.best_for(request.user).pk == run.pk and previous_best is not None
    logger.info("run saved user=%s run=%s best=%s", request.user.pk, run.pk, is_best)
    return JsonResponse({"id": run.pk, "personal_best": is_best, "first_run": previous_best is None}, status=201)


def healthz(request):
    """Render's health check: 200 "ok" only if the app can reach its database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # any database failure means unhealthy
        logger.exception("health check: database unreachable")
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    response = HttpResponse("ok", content_type="text/plain")
    response["X-App-Env"] = settings.APP_ENV
    return response
