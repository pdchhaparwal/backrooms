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
        r = self.client.get("/healthz")
        self.assertEqual(r.content, b"ok")
        self.assertEqual(r["X-App-Env"], "local")

    def test_healthz_reports_database_failure(self):
        with mock.patch("game.views.connection.cursor", side_effect=Exception("db down")):
            with self.assertLogs("game.views", level="ERROR"):
                r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 503)

    @override_settings(APP_ENV="staging")
    def test_staging_badge_shown(self):
        self.assertContains(self.client.get("/"), "env-badge")

    @override_settings(APP_ENV="production")
    def test_no_badge_on_production(self):
        self.assertNotContains(self.client.get("/"), "env-badge")


class RunTests(TestCase):
    RUN = {"seconds": 5, "distance": 7.25, "attacks": 3, "hits": 1, "touched": 2, "banished": True}

    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="pw-12345678")
        self.bob = User.objects.create_user("bob", password="pw-12345678")
        self.client.force_login(self.alice)

    def post(self, data, client=None):
        import json

        return (client or self.client).post("/runs/", json.dumps(data), content_type="application/json")

    def test_saves_run_for_session_user(self):
        r = self.post({**self.RUN, "user": self.bob.pk})  # a smuggled user id is ignored
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()["first_run"])
        from .models import Run

        run = Run.objects.get()
        self.assertEqual(run.user, self.alice)
        self.assertEqual((run.distance, run.attacks, run.hits, run.touched, run.banished), (7.25, 3, 1, 2, True))
        self.assertEqual(self.bob.runs.count(), 0)

    def test_login_required(self):
        self.client.logout()
        self.assertIn(self.post(self.RUN).status_code, (401, 403))
        from .models import Run

        self.assertFalse(Run.objects.exists())

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get("/runs/").status_code, 405)

    def test_rejects_bad_input(self):
        for bad in ({**self.RUN, "distance": -1}, {**self.RUN, "hits": 9}, {**self.RUN, "seconds": 99999}, {"distance": "far"}):
            self.assertEqual(self.post(bad).status_code, 400, bad)
        self.assertEqual(self.client.post("/runs/", "not json", content_type="application/json").status_code, 400)
        self.assertEqual(self.post([1, 2]).status_code, 400)

    def test_csrf_enforced(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.alice)
        self.assertEqual(self.post(self.RUN, client=strict).status_code, 403)

    def test_personal_best_flag(self):
        self.post({**self.RUN, "banished": False, "distance": 3})
        self.assertFalse(self.post({**self.RUN, "banished": False, "distance": 1}).json()["personal_best"])
        self.assertTrue(self.post({**self.RUN, "banished": False, "distance": 9}).json()["personal_best"])
        # banishing the entity beats any distance without banishing
        self.assertTrue(self.post({**self.RUN, "banished": True, "distance": 0.5}).json()["personal_best"])

    def test_play_now_shows_last_five_and_best(self):
        for d in range(1, 8):
            self.post({**self.RUN, "banished": False, "distance": d})
        r = self.client.get("/?v=a")
        self.assertEqual(len(r.context["recent_runs"]), 5)
        self.assertEqual(r.context["best_run"].distance, 7)
        self.assertContains(r, 'id="best-run"')
        self.assertNotContains(r, 'id="no-runs"')
        # another player's page shows none of alice's runs
        self.client.force_login(self.bob)
        r = self.client.get("/?v=b")
        self.assertContains(r, 'id="no-runs"')
        self.assertIsNone(r.context["best_run"])

    def test_play_page_has_save_hook(self):
        self.assertContains(self.client.get("/play/"), 'data-save-url="/runs/"')
