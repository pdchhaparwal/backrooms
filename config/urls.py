from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

from assistant import views as assistant
from game import views as game

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", game.VariantLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/signup/", game.signup, name="signup"),
    path("", game.home, name="home"),
    path("instructions/", game.instructions, name="instructions"),
    path("play/", game.play, name="play"),
    path("runs/", game.save_run, name="save-run"),
    path("runs/started/", game.run_started, name="run-started"),
    path("experiment/", game.experiment_results, name="experiment"),
    path("assistant/radio/", assistant.radio, name="assistant-radio"),
    path("healthz", game.healthz, name="healthz"),
    path("", include("abtest.urls")),
]
