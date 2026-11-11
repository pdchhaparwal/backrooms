"""Create the grader accounts. Safe to run any number of times.

Passwords come from environment variables (never committed):
  SEED_ADMIN_PASSWORD   -> admin@example.com (superuser, can open /admin)
  SEED_PLAYER_PASSWORD  -> player1@example.com, player2@example.com

With DEBUG=true and no env var set, a local-only default is used.
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

LOCAL_DEFAULT_PASSWORD = "backrooms-local-only"

ACCOUNTS = [
    {"username": "admin@example.com", "env": "SEED_ADMIN_PASSWORD", "admin": True},
    {"username": "player1@example.com", "env": "SEED_PLAYER_PASSWORD", "admin": False},
    {"username": "player2@example.com", "env": "SEED_PLAYER_PASSWORD", "admin": False},
]


class Command(BaseCommand):
    help = "Create or update the grader accounts (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()
        for spec in ACCOUNTS:
            user, created = User.objects.get_or_create(username=spec["username"])
            user.email = spec["username"]
            user.is_staff = spec["admin"]
            user.is_superuser = spec["admin"]
            user.is_active = True

            password = os.environ.get(spec["env"]) or (LOCAL_DEFAULT_PASSWORD if settings.DEBUG else None)
            if password:
                user.set_password(password)
            elif created:
                user.set_unusable_password()
                self.stderr.write(self.style.WARNING(f"{spec['env']} not set: {spec['username']} cannot log in yet"))
            user.save()
            self.stdout.write(f"{'created' if created else 'updated'} {spec['username']}")
        self.stdout.write(self.style.SUCCESS("seed complete"))
