# Technical challenge and testing strategy

Work in progress. Updated each sprint.

## Technical-challenge items

### 1. Delivery: CI, CD to staging, deliberate promotion to production, health checks
- **What:** every pull request runs the migrations check, Django system checks and the full test suite on a real Postgres service. Merging to `main` deploys staging. Production deploys only from the `production` branch, which moves only when someone runs the **Promote to production** action (a fast-forward, which refuses to overwrite production with unrelated history). `/healthz` returns 200 only if the database answers, and Render uses it as the health check.
- **Files:** `.github/workflows/ci.yml`, `.github/workflows/promote.yml`, `render.yaml`, `game/views.py` (`healthz`), `config/settings.py` (`APP_ENV`; deployed environments refuse to start without `DATABASE_URL`)
- **See it:** the Actions tab on any pull request; `/healthz` on staging and production; the red STAGING badge in the nav on staging only.

### 2. AI: structured LLM output that drives the game, with per-user usage limits
- **What:** "the radio". The game sends the current situation (numbers and flags only, validated by `SituationForm`). The server asks the model for JSON `{"hint", "journal"}`, parses and clips it, and shows it in the game. If there is no key, the call times out or returns an HTTP error, or the JSON is unusable, built-in rules answer instead. Each reply is stored with its source, model, latency and fallback reason. Each player gets 40 replies per 24 hours (HTTP 429 after that, without calling the LLM).
- **Files:** `assistant/llm.py`, `assistant/views.py`, `assistant/models.py`, `game/static/game/backrooms.js` (`askRadio`)
- **See it:** play, press `H`; finish a run and read the journal on the end screen; admin → *Radio messages*.
- **Next:** hints about the exit door (Sprint 3) and an evaluation set of situations run like tests.

### 3. (Sprint 3 candidate) Measured experiment on the Play Now page
- **What:** each session's first Play Now design is recorded once, and its first run started counts as a conversion. Staff see the conversion rate per design at `/experiment/`.
- **Files:** `game/experiment.py`, `game/models.py` (`PlayNowView`, `PlayNowStart`)

## Testing strategy
- **Unit and integration tests (Django `TestCase`, run on Postgres in CI):** A/B counting rules and stats; seed idempotency; auth and page variants; saving runs (validation, CSRF, a run can't be saved for another user, best-run ordering); the Play Now experiment (one view per session, one conversion); the radio endpoint (login, CSRF, validation, daily limit, linking only your own run) and every LLM failure path.
- **What we mock:** the OpenRouter HTTP call (`assistant.llm.requests.post`). The radio tests also patch `requests.Session.request` to raise, so any accidental real network call fails the test. CI has no API key.
- **Manual browser checks:** before each PR, the game flow in a real browser (run saved, radio hint, journal, Play Now history), plus screenshots of both page variants.
- **Not tested automatically (yet):** the canvas rendering and game physics in `backrooms.js` (checked by playing; Playwright end-to-end tests are a Sprint 3 candidate), and the real model's wording (the fallback rules are tested; an evaluation set comes next).
