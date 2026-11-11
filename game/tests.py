from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

ENV = {"SEED_ADMIN_PASSWORD": "admin-pass-123", "SEED_PLAYER_PASSWORD": "player-pass-123"}


class SeedTests(TestCase):
    def run_seed(self):
        call_command("seed", stdout=StringIO(), stderr=StringIO())

    @mock.patch.dict("os.environ", ENV)
    def test_creates_grader_accounts_and_is_idempotent(self):
        self.run_seed()
        self.run_seed()
        User = get_user_model()
        self.assertEqual(User.objects.count(), 3)
        admin = User.objects.get(username="admin@example.com")
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.assertTrue(admin.check_password("admin-pass-123"))
        for name in ("player1@example.com", "player2@example.com"):
            u = User.objects.get(username=name)
            self.assertFalse(u.is_staff)
            self.assertTrue(u.check_password("player-pass-123"))

    @mock.patch.dict("os.environ", ENV)
    def test_seeded_player_can_log_in(self):
        self.run_seed()
        r = self.client.post("/accounts/login/", {"username": "player1@example.com", "password": "player-pass-123"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)

    @override_settings(DEBUG=False)
    @mock.patch.dict("os.environ", {}, clear=True)
    def test_missing_passwords_do_not_crash(self):
        self.run_seed()
        self.assertFalse(get_user_model().objects.get(username="admin@example.com").has_usable_password())


class AuthFlowTests(TestCase):
    def test_pages_require_login(self):
        for url in ("/", "/instructions/", "/play/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302)
            self.assertIn("/accounts/login/", r["Location"])

    def test_signup_logs_in_and_logout_works(self):
        r = self.client.post(
            "/accounts/signup/",
            {"username": "wanderer", "password1": "yellow-wallpaper-9", "password2": "yellow-wallpaper-9"},
        )
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.client.post("/accounts/logout/")
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_full_flow_pages_render(self):
        user = get_user_model().objects.create_user("p", password="pw-12345678")
        self.client.force_login(user)
        self.assertContains(self.client.get("/"), 'id="play-now"')
        self.assertContains(self.client.get("/instructions/"), 'id="start-game"')
        r = self.client.get("/play/")
        self.assertContains(r, 'id="view"')
        self.assertContains(r, 'data-seconds="5"')
        self.assertContains(self.client.get("/play/?t=30"), 'data-seconds="30"')


class VariantTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("v", password="pw-12345678"))

    def test_forced_variant_sticks(self):
        self.assertContains(self.client.get("/?v=b"), "FOUND FOOTAGE")
        self.assertContains(self.client.get("/"), "FOUND FOOTAGE")
        self.assertContains(self.client.get("/?v=a"), "Mono-yellow")
        self.assertContains(self.client.get("/"), "Mono-yellow")

    def test_every_variant_renders(self):
        for v in ("a", "b"):
            self.assertEqual(self.client.get(f"/?v={v}").status_code, 200)
            self.assertEqual(self.client.get(f"/instructions/?v={v}").status_code, 200)
        self.client.logout()
        self.assertContains(self.client.get("/accounts/login/?v=a"), "ENTER LEVEL 0")
        self.assertContains(self.client.get("/accounts/login/?v=b"), "IDENTIFY YOURSELF")

    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz").content, b"ok")
