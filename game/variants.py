"""Per-visitor UI variants for the login, Play Now and instructions pages.

Each visitor gets a random variant per page that sticks for their session.
Force one with ?v=a or ?v=b (it then sticks too), which makes manual testing easy.
"""

import random

VARIANTS = ("a", "b")


def pick(request, page):
    key = f"ui_variant_{page}"
    forced = request.GET.get("v")
    if forced in VARIANTS:
        request.session[key] = forced
    elif request.session.get(key) not in VARIANTS:
        request.session[key] = random.choice(VARIANTS)
    return request.session[key]


def context(variant):
    other = "b" if variant == "a" else "a"
    return {"variant": variant, "other_variant": other, "theme": f"theme-{variant}"}
