import hashlib

from django.conf import settings
from django.urls import re_path
from django.views.generic import RedirectView

from . import views

h = settings.AB_HASH

# Sprint 1 used the wrong nickname ("656-mba-backrooms" -> /ef88062). Keep old links working.
LEGACY_HASH = hashlib.sha1(b"656-mba-backrooms").hexdigest()[:7]

urlpatterns = [
    re_path(rf"^{h}/?$", views.page, name="abtest-page"),
    re_path(rf"^{h}/click/?$", views.click, name="abtest-click"),
    re_path(rf"^{h}/stats/?$", views.stats, name="abtest-stats"),
]

if LEGACY_HASH != h:
    urlpatterns += [
        re_path(rf"^{LEGACY_HASH}/?$", RedirectView.as_view(pattern_name="abtest-page", permanent=False)),
        re_path(rf"^{LEGACY_HASH}/stats/?$", RedirectView.as_view(pattern_name="abtest-stats", permanent=False)),
    ]
