# The Backrooms — MGT656 team `656-mba-backrooms`

A small first-person web game set in "Level 0" of the Backrooms: endless mono-yellow hallways, damp carpet, humming fluorescent lights, and something walking toward you.

This repo is our **Sprint 1 walking skeleton**: the whole pipeline (accounts → database → staging deploy → A/B test → backlog) works end to end, with a short playable demo on top.

| | |
|---|---|
| **Staging app** | https://backrooms-staging.onrender.com |
| **A/B test page** | https://backrooms-staging.onrender.com/ef88062 |
| **A/B stats (JSON)** | https://backrooms-staging.onrender.com/ef88062/stats |
| **Project board** | https://github.com/users/pdchhaparwal/projects/2 |
| **Backlog** | [Issues labeled `user story`](https://github.com/pdchhaparwal/backrooms/issues?q=label%3A%22user+story%22) |
| **Sprint 1 report** | [`docs/mgt656/sprints/sprint-1.md`](docs/mgt656/sprints/sprint-1.md) |

> **Heads-up:** staging runs on Render's free tier, which sleeps after ~15 minutes of inactivity. The first request after a nap can take **up to ~50 seconds**. After that it's fast.

---

## Contents
1. [Quick start for graders](#1-quick-start-for-graders)
2. [How to play](#2-how-to-play)
3. [Page variants (login, Play Now, instructions)](#3-page-variants)
4. [The A/B test page](#4-the-ab-test-page)
5. [Tech stack and architecture](#5-tech-stack-and-architecture)
6. [Repository layout](#6-repository-layout)
7. [Run it locally](#7-run-it-locally)
8. [Tests](#8-tests)
9. [Seed command and grader accounts](#9-seed-command-and-grader-accounts)
10. [Deploying to staging (Render + Neon)](#10-deploying-to-staging-render--neon)
11. [Configuration reference](#11-configuration-reference)
12. [How we work: sprints, backlog, board](#12-how-we-work-sprints-backlog-board)
13. [Troubleshooting](#13-troubleshooting)
14. [Team](#14-team)

---

## 1. Quick start for graders

1. Open **https://backrooms-staging.onrender.com/accounts/login/** (allow up to ~50 s for the first load).
2. Log in with a seeded account. **Passwords are in our submission notes**, not in this repo.

   | Account | Role | What it can do |
   |---|---|---|
   | `admin@example.com` | Superuser | Everything below, plus the Django admin at `/admin/` |
   | `player1@example.com` | Player | Play the game |
   | `player2@example.com` | Player | Play the game |

   Or create your own account at `/accounts/signup/`.
3. Click **Play Now** → read the instructions → click **I'm ready** / **Begin tape** → press **W** to start the 5-second run.
4. Check the A/B test: open `/ef88062` in a private window, click the button, then open `/ef88062/stats`.
5. As admin, open `/admin/` → **Impressions** and **Clicks** to see the raw A/B rows with timestamps.

## 2. How to play

You start in a corridor of Level 0. A dark figure stands a few tiles ahead and walks toward you. You have **5 seconds** (the timer starts on your first key press).

| Key | Action |
|---|---|
| `W` or `↑` | Move forward |
| `S` or `↓` | Move backward |
| `A` or `←` | Turn left |
| `D` or `→` | Turn right |
| `Space` | Attack (swing the pipe) — hits if the entity is close and in front of you |
| `R` | Restart the run |
| `M` | Mute / unmute the fluorescent hum |

- A **key monitor** under the game lights up each key as you press it, so you can confirm every control registers.
- The **end screen** shows distance walked, attacks and hits, whether the entity was banished, and a checklist of which controls you tested (✓ / ·).
- Want a longer run? Add `?t=30` to the URL (`/play/?t=30` = 30 seconds; 1–600 allowed).
- The graphics are intentionally low-fi: a ~375-line software raycaster in plain JavaScript (`game/static/game/backrooms.js`) drawing to a 320×200 canvas. No libraries, no image files.

## 3. Page variants

The **login**, **Play Now** and **instructions** pages each have two designs:

| Page | Variant A — "Level 0" | Variant B — "Found footage" |
|---|---|---|
| Login `/accounts/login/` | Yellow wallpaper card, "Enter Level 0" | VHS terminal, "Identify yourself", blinking REC |
| Play Now `/` | Big flickering title, **PLAY NOW** | Tape label, **▶ PLAY NOW** |
| Instructions `/instructions/` | Table of keys | Keyboard keycap diagram |

- Each visitor gets a **random** variant per page, and it **sticks** for their session.
- Force a variant with `?v=a` or `?v=b` (e.g. `/?v=b`); the choice then sticks too.
- The footer of every variant page shows which one you're on and links to the other.
- Logic: [`game/variants.py`](game/variants.py). Templates: `game/templates/registration/login_{a,b}.html`, `game/templates/game/home_{a,b}.html`, `game/templates/game/instructions_{a,b}.html`.

These are the foundation for Sprint 2's experiment ([#4](https://github.com/pdchhaparwal/backrooms/issues/4)): measuring which Play Now design gets more players into the game.

## 4. The A/B test page

**URL:** `/<hash>` where `hash` = the first 7 hex characters of `sha1(team nickname)`.
Our nickname is `656-mba-backrooms`, so the page is **`/ef88062`** and the stats are **`/ef88062/stats`**.

```bash
python -c "import hashlib; print(hashlib.sha1(b'656-mba-backrooms').hexdigest()[:7])"   # ef88062
```

**What the page does (matches the course spec):**

| Rule | How it's implemented |
|---|---|
| Public, returns 200, no login, no pop-ups | Plain Django view, no auth decorator |
| Lists team members | Read from `docs/mgt656/team.yaml` |
| Exactly one `<button id="abtest">` reading `kudos` or `thanks` | Standalone template with a single button (no nav bar, so no other buttons) |
| Each new visitor gets a random 50/50 variant, kept in their session | `random.choice(["kudos", "thanks"])` on the **server**; visitor id stored in the Django session |
| One impression per visitor; reloads/redirects don't count again | `Impression.visitor_id` is unique; existing visitors are looked up, not re-inserted |
| Click via `<form method="post">`, at most once per visitor | `Click` has a one-to-one link to the visitor's `Impression`; duplicates are ignored |
| Redirect back adds no impression and keeps the variant | Click view redirects to `/ef88062`, which finds the existing impression |
| Impressions and clicks stored with timestamps | `created_at` on both models, in Postgres |
| `/ef88062/stats` returns live JSON with `preferred` | Computed from the database on every request |

**Example stats response:**
```json
{
  "preferred": "kudos",
  "kudos":  {"impressions": 12, "clicks": 5, "click_rate": 0.4167},
  "thanks": {"impressions": 10, "clicks": 3, "click_rate": 0.3}
}
```
`preferred` is the variant with the **higher click-through rate** (clicks ÷ impressions). Ties, including no data yet, go to `kudos`.

Code: [`abtest/`](abtest/) — `models.py`, `views.py`, `urls.py`, `tests.py`.

## 5. Tech stack and architecture

| Layer | Choice | Why |
|---|---|---|
| Framework | **Django 5.2** (Python 3.12) | Accounts, sessions, admin and migrations out of the box |
| Database | **PostgreSQL** on **Neon** (free tier) | Required by the course; managed, nothing to install |
| Hosting | **Render** web service (free tier), defined in [`render.yaml`](render.yaml) | Deploys automatically on every push to `main` |
| App server | gunicorn | Production WSGI server |
| Static files | WhiteNoise | Serves CSS/JS from the app, no CDN needed |
| Game | Vanilla JavaScript + `<canvas>` | No build step, no dependencies |

```
 Browser ──HTTPS──▶ Render (gunicorn + Django) ──DATABASE_URL──▶ Neon Postgres
                       │
                       ├─ /accounts/*        Django auth (login variants, signup, logout)
                       ├─ / /instructions/   Play Now + instructions (variants, login required)
                       ├─ /play/             game page → static/game/backrooms.js
                       ├─ /ef88062[/stats]   A/B test (public)
                       └─ /admin/            Django admin
```

It follows 12-factor conventions: all config and secrets come from environment variables, the database is attached via `DATABASE_URL`, the app binds to `$PORT`, logs go to stdout, and schema changes go through migrations.

## 6. Repository layout

```
backrooms/
├── config/                  Django project: settings.py, urls.py, wsgi.py
├── game/                    Accounts, pages, game, seed command
│   ├── views.py             login/signup/home/instructions/play/healthz
│   ├── variants.py          per-visitor A/B page variants (?v=a|b)
│   ├── management/commands/seed.py   creates grader accounts
│   ├── templates/           login_a/b, signup, home_a/b, instructions_a/b, play
│   ├── static/game/         site.css, backrooms.js (the raycaster)
│   └── tests.py
├── abtest/                  The course A/B test page
│   ├── models.py            Impression, Click
│   ├── views.py             page, click, stats
│   └── tests.py
├── templates/base.html      shared layout (nav, footer, themes)
├── docs/mgt656/
│   ├── team.yaml            team nickname + members (drives the A/B page)
│   ├── backlog.md           backlog overview
│   └── sprints/sprint-1.md  Sprint 1 report
├── scripts/create_backlog.sh   creates the user-story issues via GitHub's API
├── render.yaml              Render blueprint (staging)
├── requirements.txt
└── manage.py
```

## 7. Run it locally

Requires Python 3.12+.

```bash
git clone https://github.com/pdchhaparwal/backrooms.git
cd backrooms
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DEBUG=true                     # Windows: set DEBUG=true
python manage.py migrate
python manage.py seed                 # local password for all 3 accounts: backrooms-local-only
python manage.py runserver
```

Open http://127.0.0.1:8000. Without `DATABASE_URL` the app uses a local SQLite file (`db.sqlite3`), which is handy for quick work.

To run locally against **Postgres** (same as staging), point `DATABASE_URL` at any Postgres database before `migrate`:
```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

## 8. Tests

```bash
python manage.py test
```

24 tests, all passing on Postgres:

- **A/B counting rules:** one impression per visitor, reloads don't count, one click max, redirects keep the variant, GET on the click URL is rejected, CSRF works, both variants appear across visitors, wrong hash → 404
- **Stats:** `preferred` uses click rate, not raw clicks; stats update live; empty database still returns valid JSON
- **Seed:** creates the 3 accounts, is idempotent, seeded players can log in, missing passwords don't crash startup
- **Auth and pages:** login required for the game pages, signup → login → logout, every page variant renders, `?v=` sticks

## 9. Seed command and grader accounts

```bash
python manage.py seed
```

- Creates or updates `admin@example.com` (superuser), `player1@example.com` and `player2@example.com`.
- **Idempotent:** safe to run any number of times; it never creates duplicates.
- Passwords come from environment variables, never from git:
  - `SEED_ADMIN_PASSWORD` → admin
  - `SEED_PLAYER_PASSWORD` → both players
- On Render it runs on **every deploy**, so changing a password in Render's Environment tab and redeploying resets the account to the new password.
- Locally with `DEBUG=true` and no env vars, all three use `backrooms-local-only`.

## 10. Deploying to staging (Render + Neon)

Staging is already live; these steps are for reference or for standing up production in Sprint 2.

1. **Database (Neon):** create a project → **Connect** → choose the database and role, turn **Connection pooling off**, and copy the connection string (`postgresql://…?sslmode=require`).
2. **App (Render):** **New → Blueprint** → select this repo. Render reads `render.yaml` and asks for:
   - `DATABASE_URL` — the Neon string
   - `SEED_ADMIN_PASSWORD`, `SEED_PLAYER_PASSWORD` — grader passwords
   - (`SECRET_KEY` is generated automatically)
3. Click **Apply**. Each deploy runs:
   - build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - start: `python manage.py migrate --noinput && python manage.py seed && gunicorn config.wsgi --bind 0.0.0.0:$PORT`
4. Every push to `main` redeploys automatically.

**Healthy deploy logs look like:** `Applying … OK` → `seed complete` → `Listening at: http://0.0.0.0:10000`.

## 11. Configuration reference

| Variable | Required on Render | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | local SQLite | Postgres connection string |
| `SECRET_KEY` | Yes (auto-generated) | insecure dev key | Django signing key |
| `SEED_ADMIN_PASSWORD` | Yes | — | Password for `admin@example.com` |
| `SEED_PLAYER_PASSWORD` | Yes | — | Password for `player1@` / `player2@example.com` |
| `PYTHON_VERSION` | Set in `render.yaml` | — | Python version on Render (3.12.8) |
| `DEBUG` | No | `false` | Debug mode; local only |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Extra hostnames (Render's hostname is added automatically) |
| `DEMO_SECONDS` | No | `5` | Length of a game run |
| `TEAM_NICKNAME` | No | from `team.yaml` | Override the nickname used for the A/B hash |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## 12. How we work: sprints, backlog, board

- **Board:** [Backrooms project](https://github.com/users/pdchhaparwal/projects/2). The **View 1** tab shows status (Todo / In Progress / Done); the **Sprints** tab shows stories by iteration.
- **Iterations:** Sprint 1 Nov 3–11 · Sprint 2 Nov 12–18 · Sprint 3 Nov 19–Dec 2 · Sprint 4 Dec 3–11.
- **Backlog:** every story is a GitHub issue labeled `user story`, written as *"As a …, I want …, so that …"* with acceptance criteria as a checklist.

  | Sprint | Stories |
  |---|---|
  | 1 | [#1](https://github.com/pdchhaparwal/backrooms/issues/1) Walking skeleton (done) |
  | 2 | [#2](https://github.com/pdchhaparwal/backrooms/issues/2) Production env · [#3](https://github.com/pdchhaparwal/backrooms/issues/3) Save runs + personal best · [#4](https://github.com/pdchhaparwal/backrooms/issues/4) Play Now variant experiment |
  | 3 | [#5](https://github.com/pdchhaparwal/backrooms/issues/5) Exit door · [#6](https://github.com/pdchhaparwal/backrooms/issues/6) Entity chases you · [#7](https://github.com/pdchhaparwal/backrooms/issues/7) New layout every run |
  | 4 | [#8](https://github.com/pdchhaparwal/backrooms/issues/8) Touch controls · [#9](https://github.com/pdchhaparwal/backrooms/issues/9) Reduced-flicker + sound settings · [#10](https://github.com/pdchhaparwal/backrooms/issues/10) Leaderboard |

- **Sprint reports:** `docs/mgt656/sprints/sprint-N.md`, on `main` before each deadline.
- **Team file:** `docs/mgt656/team.yaml` — team nickname plus each member's nickname and GitHub username. The app reads this file, so the A/B page updates automatically when it changes.
- **Workflow (from Sprint 2):** branch → pull request → teammate review → merge to `main` → Render deploys staging.

## 13. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Staging takes ~50 s to load | Free tier was asleep. Wait; later requests are fast. |
| `Bad Request (400)` | The hostname isn't allowed. Render's own hostname is added automatically; for a custom domain, add it to `ALLOWED_HOSTS`. |
| `CSRF verification failed` on login | Usually an old tab. Reload the page and submit again. |
| A/B stats reset to 0 after a deploy | `DATABASE_URL` is missing, so the app fell back to temporary SQLite. Set it in Render → Environment. |
| Grader account can't log in | Check `SEED_ADMIN_PASSWORD` / `SEED_PLAYER_PASSWORD` in Render, then redeploy (seed resets the passwords). |
| Game doesn't react to keys | Click on the page once so it has focus, then press `W`. |
| No hum | Browsers block audio until you press a key; press `M` to toggle. |

## 14. Team

Team nickname: **`656-mba-backrooms`**

| GitHub |
|---|
| [@pdchhaparwal](https://github.com/pdchhaparwal) |
| [@apoorve-tyagi](https://github.com/apoorve-tyagi) |
| [@PrabhashC](https://github.com/PrabhashC) |
| [@keshhh](https://github.com/keshhh) |
| [@GLM321](https://github.com/GLM321) |
| [@shashwatb10](https://github.com/shashwatb10) |

Built for MGT656 (Management of Software Development), Yale School of Management, Fall 2026.
