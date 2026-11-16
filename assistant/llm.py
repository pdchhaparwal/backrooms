"""Talking to the LLM through OpenRouter, server side only.

`ask_radio(situation)` returns a Reply with a hint and a journal entry. It never
raises: if there is no API key, the request fails or times out, or the model's JSON
is unusable, it returns the built-in rule-based reply and says why.

Tests mock `requests.post`; they never call OpenRouter.
"""

import json
import logging
import re
import time
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_HINT = 240
MAX_JOURNAL = 360

SYSTEM_PROMPT = """You are "the radio": a crackling handheld radio found in Level 0 of the Backrooms,
in a found-footage horror game. The player is a lost wanderer. Each time you are asked,
you get the current game situation as JSON and reply with:

- "hint": ONE cryptic but genuinely useful survival hint, grounded only in the situation
  given. Point toward what to do next without spelling out controls or numbers
  (say "it is close behind you", not "entity_distance is 1.2"). Max 200 characters.
- "journal": a 1-3 sentence eerie journal entry, first person, as the wanderer writing
  about what just happened. Max 300 characters.

Facts about the game you may rely on: an entity walks toward the player; swinging the
pipe banishes it only if it is close AND in front of the player; walking further is
better; when the run ends the clock has run out. Do not invent items, exits or rooms.

Reply with ONLY a JSON object: {"hint": "...", "journal": "..."}"""


@dataclass
class Reply:
    hint: str
    journal: str
    source: str  # "llm" or "fallback"
    model: str = ""
    latency_ms: int | None = None
    error: str = ""


def ask_radio(situation):
    key = settings.OPENROUTER_API_KEY
    if not key:
        return fallback(situation, error="no OPENROUTER_API_KEY configured")

    model = settings.OPENROUTER_MODEL
    started = time.monotonic()
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-Title": "The Backrooms (MGT656)",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(situation, sort_keys=True)},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 300,
                "temperature": 0.9,
            },
            timeout=settings.OPENROUTER_TIMEOUT,
        )
        latency = int((time.monotonic() - started) * 1000)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        hint, journal = parse_reply(content)
    except requests.Timeout:
        return fallback(situation, error="OpenRouter timed out")
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning("OpenRouter request failed: %s", status or exc.__class__.__name__)
        return fallback(situation, error=f"OpenRouter error {status or exc.__class__.__name__}")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("OpenRouter reply unusable: %s", exc)
        return fallback(situation, error=f"unusable reply: {exc}"[:200])

    logger.info("radio reply model=%s latency_ms=%s", model, latency)
    return Reply(hint=hint, journal=journal, source="llm", model=model, latency_ms=latency)


def parse_reply(content):
    """Pull {"hint", "journal"} out of the model's text; raise ValueError if we can't."""
    if not isinstance(content, str):
        raise ValueError("content is not text")
    match = re.search(r"\{.*\}", content, re.DOTALL)  # tolerate ```json fences or chatter
    if not match:
        raise ValueError("no JSON object in reply")
    data = json.loads(match.group(0))
    hint, journal = data.get("hint"), data.get("journal")
    if not (isinstance(hint, str) and hint.strip() and isinstance(journal, str) and journal.strip()):
        raise ValueError("missing hint or journal")
    return _clip(hint, MAX_HINT), _clip(journal, MAX_JOURNAL)


def _clip(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fallback(situation, error=""):
    """Rule-based reply so the radio still says something useful without the LLM."""
    alive = situation.get("entity_alive")
    near = situation.get("entity_distance", 99) < 2.0
    ahead = situation.get("entity_ahead")
    if alive and near and ahead:
        hint = "It is right in front of you. Swing now, before it closes the gap."
    elif alive and near:
        hint = "It is close, but not where you are looking. Turn to face it."
    elif alive:
        hint = "It keeps walking toward you. Let it come, face it, and wait until it is close."
    elif situation.get("distance", 0) < 3:
        hint = "The hallway goes on. Keep moving; standing still is how they find you."
    else:
        hint = "The hum is quieter now. Keep walking while it lasts."

    if situation.get("phase") == "ended":
        journal = (
            "The lights buzzed louder when the tape ran out. I swung at it and it came apart like static."
            if not alive
            else "The tape ran out. I could still hear it walking somewhere behind the wallpaper."
        )
    else:
        journal = "Same yellow walls. Same carpet smell. The radio only works when I'm scared."
    return Reply(hint=hint, journal=journal, source="fallback", error=error[:200])
