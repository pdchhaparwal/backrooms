from django.conf import settings


def app_env(request):
    """Expose which environment this is (local / staging / production) to templates."""
    return {"app_env": settings.APP_ENV}
