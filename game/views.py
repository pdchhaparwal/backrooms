from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.shortcuts import redirect, render

from . import variants


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
    return render(request, f"game/home_{v}.html", variants.context(v))


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


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")
