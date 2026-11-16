# Sprint 2 report: production, first player features, the radio

## Sprint goal
Stand up **production** next to staging with its own database and a deliberate promote step, ship the first player-facing stories through reviewed pull requests, and get the AI feature (the radio, our survival assistant) working end to end.

## What shipped
Every change went branch → pull request (`Closes #N`) → CI → teammate review → merge to `main` → staging.

- **Production environment** — [#2](https://github.com/pdchhaparwal/backrooms/issues/2), [PR](https://github.com/pdchhaparwal/backrooms/pulls?q=is%3Apr+head%3Aproduction-env)
  - `render.yaml` defines `backrooms-staging` (deploys `main`) and `backrooms-production` (deploys the `production` branch), each with its own Neon Postgres `DATABASE_URL`
  - Promoting is deliberate: the **Promote to production** GitHub Action fast-forwards `production` to `main`
  - CI (GitHub Actions) runs the migrations check, Django checks and all tests on Postgres for every pull request
  - `/healthz` checks the database (503 if it is down) and is Render's health check; a deployed app refuses to boot without `DATABASE_URL` instead of silently using SQLite; a STAGING badge marks staging pages
- **Save each run and show a personal best** — [#3](https://github.com/pdchhaparwal/backrooms/issues/3), [PR](https://github.com/pdchhaparwal/backrooms/pulls?q=is%3Apr+head%3Asave-runs)
  - Each finished run is saved for the logged-in player (`POST /runs/`, validated, CSRF-protected, user always taken from the session); Play Now lists the last 5 runs and the best one
- **Play Now experiment** — [#4](https://github.com/pdchhaparwal/backrooms/issues/4), [PR](https://github.com/pdchhaparwal/backrooms/pulls?q=is%3Apr+head%3Aplay-now-experiment)
  - Each session's first Play Now view records its design; the first run it starts counts as a conversion; staff see the conversion rate per design at `/experiment/`
- **AI survival assistant, first slice** — [AI story](https://github.com/pdchhaparwal/backrooms/issues?q=is%3Aissue+%22survival+assistant%22), [PR](https://github.com/pdchhaparwal/backrooms/pulls?q=is%3Apr+head%3Aai-survival-assistant)
  - Press `H` for a hint about your current situation; the end screen shows a journal entry about the run. The server calls OpenRouter, asks for JSON `{"hint", "journal"}`, validates and clips it, and falls back to built-in rules on no key, timeout, HTTP error or bad JSON. Replies are stored; 40 per player per day
- **A/B page fix** — [PR](https://github.com/pdchhaparwal/backrooms/pulls?q=is%3Apr+head%3Afix%2Fab-team-nickname): our course team nickname is `mighty-frog`, so the A/B page moved to **`/afcf5a1`** (the Sprint 1 URL `/ef88062` redirects there without counting an impression)
- Tests: 24 → 55, all passing; none calls the real LLM

## What works now
- **Staging** https://backrooms-staging.onrender.com and **production** https://backrooms-production.onrender.com: sign up / log in, Play Now with your run history, instructions, the game with saved runs and the radio, `/afcf5a1` and `/afcf5a1/stats`, `/healthz`
- Staff (admin): `/experiment/` and the Django admin (runs, Play Now views and starts, radio messages, A/B impressions and clicks)

## Working with our AI agent
**What didn't work:** in Sprint 1 the agent built the A/B page from the team name we typed in the repo (`656-mba-backrooms`), and wrote a test that pinned that value, so everything was green while the URL was wrong. This sprint we had it check against the course's own data instead: it looked up our team in the course API, found `mighty-frog`, and the required page is `/afcf5a1`, not `/ef88062`. **What we changed:** facts that come from outside the repo (team nickname, deadlines, spec rules) are now checked against the source before the agent writes code. The test now also checks the course's worked example (`bright-forest` → `211c220`) so the hashing method itself is verified, not only our own value.

**What worked:** we gave the agent the acceptance criteria from each issue as its spec, one story per branch. For the AI feature we asked for the failure cases first (no key, timeout, HTTP 402, malformed JSON, over the daily limit). The tests mock the HTTP call and also install a guard that fails any test that tries to reach the network.

## Backlog changes for next sprint
- **New story: AI survival assistant**, labeled `user story`, in Sprint 2 and Sprint 3. Started this sprint; it carries over. The next slice is clues tied to the exit door ([#5](https://github.com/pdchhaparwal/backrooms/issues/5)): the radio hints at where the exit is without revealing it. After that, an evaluation set of situations run like tests
- Sprint 3 as planned: exit door [#5](https://github.com/pdchhaparwal/backrooms/issues/5), entity chases you [#6](https://github.com/pdchhaparwal/backrooms/issues/6), new layout every run [#7](https://github.com/pdchhaparwal/backrooms/issues/7)
- Chores: make CI a required check on `main`; replace the remaining GitHub usernames on the A/B page with course nicknames; before the Sprint 4 A/B run, delete our own test impressions and clicks on production
- Carry over: nothing else (#2, #3, #4 closed)
