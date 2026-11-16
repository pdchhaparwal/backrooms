"""Tests for the AI survival assistant. The LLM is always mocked: no test calls OpenRouter."""

import json
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from game.models import Run

from . import llm
from .models import RadioMessage

SITUATION = {
    "phase": "running", "time_left": 3.2, "seconds_total": 5, "distance": 2.5, "attacks": 1, "hits": 0,
    "touched": 0, "entity_alive": True, "entity_distance": 1.4, "entity_ahead": True,
}


def openrouter_response(content, status=200):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


GOOD = json.dumps({"hint": "It is close and in front of you. Swing.", "journal": "The wallpaper breathed tonight."})


@override_settings(OPENROUTER_API_KEY="test-key-not-real", OPENROUTER_MODEL="test/model", ASSISTANT_DAILY_LIMIT=40)
class RadioEndpointTests(TestCase):
    def setUp(self):
        # Belt and braces: fail loudly if anything reaches the real network.
        guard = mock.patch("requests.sessions.Session.request", side_effect=AssertionError("real HTTP call in a test"))
        guard.start()
        self.addCleanup(guard.stop)
        self.user = get_user_model().objects.create_user("wanderer", password="pw-12345678")
        self.client.force_login(self.user)

    def ask(self, data=None, client=None):
        return (client or self.client).post("/assistant/radio/", json.dumps(data or SITUATION), content_type="application/json")

    @mock.patch("assistant.llm.requests.post")
    def test_llm_reply_is_returned_and_stored(self, post):
        post.return_value = openrouter_response(GOOD)
        r = self.ask()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["source"], "llm")
        self.assertEqual(body["hint"], "It is close and in front of you. Swing.")
        self.assertEqual(body["remaining"], 39)

        msg = RadioMessage.objects.get()
        self.assertEqual((msg.user, msg.source, msg.model, msg.phase), (self.user, "llm", "test/model", "running"))
        self.assertEqual(msg.situation["entity_distance"], 1.4)

        # what we sent: server-side key, the chosen model, the situation as JSON, JSON mode
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key-not-real")
        self.assertEqual(kwargs["json"]["model"], "test/model")
        self.assertEqual(json.loads(kwargs["json"]["messages"][1]["content"])["phase"], "running")
        self.assertEqual(kwargs["json"]["response_format"], {"type": "json_object"})
        self.assertGreater(kwargs["timeout"], 0)

    @mock.patch("assistant.llm.requests.post")
    def test_fenced_json_is_accepted(self, post):
        post.return_value = openrouter_response("Sure!\n```json\n" + GOOD + "\n```")
        self.assertEqual(self.ask().json()["source"], "llm")

    @mock.patch("assistant.llm.requests.post")
    def test_bad_json_falls_back(self, post):
        for content in ("no json here", '{"hint": ""}', '{"hint": "x", "journal": 5}', None):
            post.return_value = openrouter_response(content)
            body = self.ask().json()
            self.assertEqual(body["source"], "fallback", content)
            self.assertTrue(body["hint"])
        self.assertTrue(all(m.error for m in RadioMessage.objects.all()))

    @mock.patch("assistant.llm.requests.post", side_effect=requests.Timeout())
    def test_timeout_falls_back(self, post):
        body = self.ask().json()
        self.assertEqual(body["source"], "fallback")
        self.assertEqual(RadioMessage.objects.get().error, "OpenRouter timed out")

    @mock.patch("assistant.llm.requests.post")
    def test_http_error_falls_back(self, post):
        post.return_value = openrouter_response("", status=402)  # e.g. out of credits
        body = self.ask().json()
        self.assertEqual(body["source"], "fallback")
        self.assertIn("402", RadioMessage.objects.get().error)

    @override_settings(OPENROUTER_API_KEY="")
    @mock.patch("assistant.llm.requests.post")
    def test_no_key_uses_rules_without_calling(self, post):
        body = self.ask().json()
        self.assertEqual(body["source"], "fallback")
        post.assert_not_called()

    @mock.patch("assistant.llm.requests.post")
    def test_long_replies_are_clipped(self, post):
        post.return_value = openrouter_response(json.dumps({"hint": "a " * 400, "journal": "b " * 400}))
        body = self.ask().json()
        self.assertLessEqual(len(body["hint"]), llm.MAX_HINT)
        self.assertLessEqual(len(body["journal"]), llm.MAX_JOURNAL)

    @override_settings(ASSISTANT_DAILY_LIMIT=2)
    @mock.patch("assistant.llm.requests.post")
    def test_daily_limit_per_player(self, post):
        post.return_value = openrouter_response(GOOD)
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(self.ask().json()["remaining"], 0)
        r = self.ask()
        self.assertEqual(r.status_code, 429)
        self.assertEqual(post.call_count, 2)  # the limited request never reached the LLM
        # another player has their own allowance
        other = Client()
        other.force_login(get_user_model().objects.create_user("other", password="pw-12345678"))
        self.assertEqual(self.ask(client=other).status_code, 200)

    @mock.patch("assistant.llm.requests.post")
    def test_links_only_your_own_run(self, post):
        post.return_value = openrouter_response(GOOD)
        mine = Run.objects.create(user=self.user, seconds=5, distance=3, attacks=1, hits=1, banished=True)
        theirs = Run.objects.create(
            user=get_user_model().objects.create_user("x", password="pw-12345678"), seconds=5, distance=1, attacks=0, hits=0
        )
        self.ask({**SITUATION, "phase": "ended", "run_id": mine.pk})
        self.ask({**SITUATION, "phase": "ended", "run_id": theirs.pk})
        runs = list(RadioMessage.objects.order_by("created_at").values_list("run_id", flat=True))
        self.assertEqual(runs, [mine.pk, None])

    def test_rejects_bad_input(self):
        for bad in ({**SITUATION, "phase": "dancing"}, {**SITUATION, "distance": -3}, {"phase": "running"}):
            self.assertEqual(self.ask(bad).status_code, 400, bad)
        self.assertEqual(self.client.post("/assistant/radio/", "nope", content_type="application/json").status_code, 400)
        self.assertFalse(RadioMessage.objects.exists())

    def test_login_and_post_required(self):
        self.assertEqual(self.client.get("/assistant/radio/").status_code, 405)
        self.client.logout()
        self.assertIn(self.ask().status_code, (401, 403))

    def test_csrf_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(self.ask(client=strict).status_code, 403)


class FallbackRulesTests(TestCase):
    def test_hints_follow_the_situation(self):
        self.assertIn("Swing", llm.fallback(SITUATION).hint)
        self.assertIn("Turn", llm.fallback({**SITUATION, "entity_ahead": False}).hint)
        self.assertIn("walking toward you", llm.fallback({**SITUATION, "entity_distance": 6}).hint)
        self.assertIn("Keep", llm.fallback({**SITUATION, "entity_alive": False}).hint)
        ended = llm.fallback({**SITUATION, "phase": "ended", "entity_alive": False})
        self.assertIn("static", ended.journal)
