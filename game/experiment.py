"""Which Play Now design gets more players to start a run? (story #4)

A session's first Play Now view records its variant; the first run that session
starts records a conversion. Forcing ?v= later does not move a session to the
other arm, so each session counts once, in the arm it first saw.
"""

import uuid

from django.db import IntegrityError, transaction

from .models import PlayNowStart, PlayNowView

SESSION_KEY = "playnow_visitor_id"


def record_view(request, variant):
    if request.session.get(SESSION_KEY):
        return
    view = PlayNowView.objects.create(
        visitor_id=str(uuid.uuid4()),
        variant=variant,
        user=request.user if request.user.is_authenticated else None,
    )
    request.session[SESSION_KEY] = view.visitor_id


def record_start(request):
    """Returns True if this call counted a new conversion."""
    visitor_id = request.session.get(SESSION_KEY)
    view = PlayNowView.objects.filter(visitor_id=visitor_id).first() if visitor_id else None
    if view is None:
        return False
    try:
        with transaction.atomic():
            _, created = PlayNowStart.objects.get_or_create(view=view)
    except IntegrityError:  # two tabs starting at the same instant
        return False
    return created


def summary():
    rows = []
    for code, label in PlayNowView.VARIANTS:
        views = PlayNowView.objects.filter(variant=code).count()
        starts = PlayNowStart.objects.filter(view__variant=code).count()
        rows.append({"variant": code, "label": label, "views": views, "starts": starts,
                     "rate": starts / views if views else 0.0})
    return rows
