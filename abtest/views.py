"""A/B test page per the MGT656 spec.

GET  /<hash>        public page, one <button id="abtest"> reading "kudos" or "thanks"
POST /<hash>/click  counts at most one click per visitor, then redirects back
GET  /<hash>/stats  live JSON from the database, including "preferred"
"""

import random
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import VARIANTS, Click, Impression

SESSION_KEY = "abtest_visitor_id"


def _current_impression(request):
    visitor_id = request.session.get(SESSION_KEY)
    if not visitor_id:
        return None
    return Impression.objects.filter(visitor_id=visitor_id).first()


@never_cache
@require_GET
def page(request):
    impression = _current_impression(request)
    if impression is None:
        # New visitor: random 50/50 assignment, chosen on the server, kept in the session.
        impression = Impression.objects.create(visitor_id=str(uuid.uuid4()), variant=random.choice(VARIANTS))
        request.session[SESSION_KEY] = impression.visitor_id
    return render(
        request,
        "abtest/page.html",
        {
            "variant": impression.variant,
            "team_nickname": settings.TEAM_NICKNAME,
            "members": settings.TEAM_MEMBER_NICKNAMES,
            "ab_hash": settings.AB_HASH,
        },
    )


@require_POST
def click(request):
    impression = _current_impression(request)
    if impression is not None:
        try:
            with transaction.atomic():
                Click.objects.get_or_create(impression=impression)
        except IntegrityError:
            pass  # simultaneous double-submit: the first one already counted
    return redirect("abtest-page")


def _summary():
    data = {}
    for v in VARIANTS:
        impressions = Impression.objects.filter(variant=v).count()
        clicks = Click.objects.filter(impression__variant=v).count()
        data[v] = {
            "impressions": impressions,
            "clicks": clicks,
            "click_rate": round(clicks / impressions, 4) if impressions else 0.0,
        }
    return data


@never_cache
@require_GET
def stats(request):
    data = _summary()
    # Preferred = higher click-through rate; ties (including no data) go to "kudos".
    preferred = "thanks" if data["thanks"]["click_rate"] > data["kudos"]["click_rate"] else "kudos"
    return JsonResponse({"preferred": preferred, **data})
