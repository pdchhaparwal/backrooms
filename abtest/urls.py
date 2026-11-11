from django.conf import settings
from django.urls import re_path

from . import views

h = settings.AB_HASH

urlpatterns = [
    re_path(rf"^{h}/?$", views.page, name="abtest-page"),
    re_path(rf"^{h}/click/?$", views.click, name="abtest-click"),
    re_path(rf"^{h}/stats/?$", views.stats, name="abtest-stats"),
]
