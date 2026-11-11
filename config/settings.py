"""Django settings. Everything environment-specific comes from env vars (12-factor)."""

import hashlib
import os
from pathlib import Path

import dj_database_url
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key-change-me")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Render sets this automatically for web services.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "game",
    "abtest",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Postgres via DATABASE_URL on staging/production. Local dev falls back to SQLite.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# Behind Render's TLS-terminating proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_COOKIES = env_bool("SECURE_COOKIES", bool(RENDER_EXTERNAL_HOSTNAME))
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES

# Logs go to stdout.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

# ---------------------------------------------------------------------------
# Team config: docs/mgt656/team.yaml is the single source of truth.
# The A/B page lives at /<first 7 hex chars of sha1(team nickname)>.
# ---------------------------------------------------------------------------
TEAM_FILE = BASE_DIR / "docs" / "mgt656" / "team.yaml"
with open(TEAM_FILE, encoding="utf-8") as fh:
    TEAM = yaml.safe_load(fh) or {}

TEAM_NICKNAME = os.environ.get("TEAM_NICKNAME") or TEAM.get("team", "")
TEAM_MEMBER_NICKNAMES = [m["nickname"] for m in TEAM.get("members", [])]
AB_HASH = hashlib.sha1(TEAM_NICKNAME.encode("utf-8")).hexdigest()[:7]

# Length of the playable demo, in seconds (override per run with /play/?t=30).
DEMO_SECONDS = int(os.environ.get("DEMO_SECONDS", "5"))
