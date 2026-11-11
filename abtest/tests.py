import hashlib
import re

from django.conf import settings
from django.test import Client, TestCase

from .models import Click, Impression

URL = f"/{settings.AB_HASH}"


def button_text(response):
    html = response.content.decode()
    assert html.count('id="abtest"') == 1, "expected exactly one #abtest element"
    assert html.count("<button") == 1, "expected exactly one button on the page"
    return re.search(r'<button id="abtest"[^>]*>([^<]*)</button>', html).group(1)


class HashTests(TestCase):
    def test_hash_is_sha1_of_team_nickname(self):
        self.assertEqual(settings.AB_HASH, hashlib.sha1(settings.TEAM_NICKNAME.encode()).hexdigest()[:7])

    def test_team_nickname_hash(self):
        self.assertEqual(settings.TEAM_NICKNAME, "656-mba-backrooms")
        self.assertEqual(settings.AB_HASH, "ef88062")


class PageTests(TestCase):
    def test_public_200_lists_members_and_one_button(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertIn(button_text(r), ["kudos", "thanks"])
        for m in settings.TEAM_MEMBER_NICKNAMES:
            self.assertContains(r, m)

    def test_trailing_slash_also_works(self):
        self.assertEqual(self.client.get(URL + "/").status_code, 200)

    def test_wrong_hash_404(self):
        self.assertEqual(self.client.get("/0000000").status_code, 404)

    def test_reloads_count_one_impression_and_keep_variant(self):
        first = button_text(self.client.get(URL))
        for _ in range(5):
            self.assertEqual(button_text(self.client.get(URL)), first)
        self.assertEqual(Impression.objects.count(), 1)
        self.assertIsNotNone(Impression.objects.get().created_at)

    def test_click_counts_once_and_redirect_back_adds_nothing(self):
        first = button_text(self.client.get(URL))
        for _ in range(3):
            r = self.client.post(f"{URL}/click")
            self.assertRedirects(r, URL, fetch_redirect_response=False)
        self.assertEqual(button_text(self.client.get(URL)), first)  # following the redirect
        self.assertEqual(Click.objects.count(), 1)
        self.assertEqual(Impression.objects.count(), 1)
        self.assertIsNotNone(Click.objects.get().created_at)
        self.assertEqual(Click.objects.get().impression.variant, first)

    def test_click_without_a_visit_counts_nothing(self):
        self.client.post(f"{URL}/click")
        self.assertEqual(Click.objects.count(), 0)

    def test_get_on_click_url_is_rejected(self):
        self.assertEqual(self.client.get(f"{URL}/click").status_code, 405)

    def test_new_visitors_get_both_variants(self):
        seen = {button_text(Client().get(URL)) for _ in range(60)}
        self.assertEqual(seen, {"kudos", "thanks"})
        self.assertEqual(Impression.objects.count(), 60)

    def test_csrf_enforced_form_still_works(self):
        c = Client(enforce_csrf_checks=True)
        r = c.get(URL)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.content.decode()).group(1)
        r = c.post(f"{URL}/click", {"csrfmiddlewaretoken": token})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Click.objects.count(), 1)


class StatsTests(TestCase):
    def _seed(self, variant, impressions, clicks):
        for i in range(impressions):
            imp = Impression.objects.create(visitor_id=f"{variant}{i}", variant=variant)
            if i < clicks:
                Click.objects.create(impression=imp)

    def test_preferred_uses_click_rate_not_raw_clicks(self):
        self._seed("kudos", 10, 2)  # 20%
        self._seed("thanks", 2, 1)  # 50%
        data = self.client.get(f"{URL}/stats").json()
        self.assertEqual(data["preferred"], "thanks")
        self.assertEqual(data["kudos"]["impressions"], 10)
        self.assertEqual(data["kudos"]["clicks"], 2)

    def test_stats_are_live(self):
        self.assertEqual(self.client.get(f"{URL}/stats").json()["preferred"], "kudos")
        self._seed("thanks", 1, 1)
        self.assertEqual(self.client.get(f"{URL}/stats").json()["preferred"], "thanks")

    def test_empty_database_is_valid_json(self):
        r = self.client.get(f"{URL}/stats")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertIn(r.json()["preferred"], ["kudos", "thanks"])

    def test_end_to_end_visit_and_click_shows_in_stats(self):
        variant = button_text(self.client.get(URL))
        self.client.post(f"{URL}/click")
        data = self.client.get(f"{URL}/stats").json()
        self.assertEqual(data[variant], {"impressions": 1, "clicks": 1, "click_rate": 1.0})
        self.assertEqual(data["preferred"], variant)
