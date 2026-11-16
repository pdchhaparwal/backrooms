# Sprint 2 report: production, first player features, the radio

## Sprint goal
Stand up **production** next to staging with its own database and a deliberate promote step, ship the first player-facing stories through reviewed pull requests, and get the AI feature (the radio, our survival assistant) working end to end.

## What shipped
Every change went branch → pull request (`Closes #N`) → CI → teammate review (Apoorve approved #12–#15; his review held back #16, see below) → merge to `main` → staging → **Promote to production**.

- **Production environment** — [#2](https://github.com/pdchhaparwal/backrooms/issues/2), PR [#13](https://github.com/pdchhaparwal/backrooms/pull/13)
  - `render.yaml` defines `backrooms-staging` (deploys `main`) and `backrooms-production` (deploys the `production` branch), each with its own Neon Postgres `DATABASE_URL`
  - Promoting is deliberate: the **Promote to production** GitHub Action fast-forwards `production` to `main`
  - CI (GitHub Actions) runs the migrations check, Django checks and all tests on Postgres for every pull request
  - `/healthz` checks the database (503 if it is down) and is Render's health check; a deployed app refuses to boot without `DATABASE_URL` instead of silently using SQLite; a STAGING badge marks staging pages
- **Save each run and show a personal best** — [#3](https://github.com/pdchhaparwal/backrooms/issues/3), PR [#14](https://github.com/pdchhaparwal/backrooms/pull/14)
  - Each finished run is saved for the logged-in player (`POST /runs/`, validated, CSRF-protected, user always taken from the session); Play Now lists the last 5 runs and the best one
- **Play Now experiment** — [#4](https://github.com/pdchhaparwal/backrooms/issues/4), PR [#15](https://github.com/pdchhaparwal/backrooms/pull/15)
  - Each session's first Play Now view records its design; the first run it starts counts as a conversion; staff see the conversion rate per design at `/experiment/`
- **AI survival assistant, first slice** — [#11](https://github.com/pdchhaparwal/backrooms/issues/11), PR [#16](https://github.com/pdchhaparwal/backrooms/pull/16)
  - Press `H` for a hint about your current situation; the end screen shows a journal entry about the run. The server calls OpenRouter, asks for JSON `{"hint", "journal"}`, validates and clips it, and falls back to built-in rules on no key, timeout, HTTP error or bad JSON. Replies are stored; 40 per player per day
- **A/B page fix** — PR [#12](https://github.com/pdchhaparwal/backrooms/pull/12): our course team nickname is `mighty-frog`, so the A/B page moved to **`/afcf5a1`** (the Sprint 1 URL `/ef88062` redirects there without counting an impression)
- Tests: 24 → 55, all passing; none calls the real LLM

## What works now
- **Staging** https://backrooms-staging.onrender.com and **production** https://backrooms-production.onrender.com: sign up / log in, Play Now with your run history, instructions, the game with saved runs and the radio, `/afcf5a1` and `/afcf5a1/stats`, `/healthz`
- Staff (admin): `/experiment/` and the Django admin (runs, Play Now views and starts, radio messages, A/B impressions and clicks)

## Working with our AI agent
**What didn't work:** in Sprint 1 the agent built the A/B page from the team name we typed in the repo (`656-mba-backrooms`), and wrote a test that pinned that value, so everything was green while the URL was wrong. This sprint we had it check against the course's own data instead: it looked up our team in the course API, found `mighty-frog`, and the required page is `/afcf5a1`, not `/ef88062`. **What we changed:** facts that come from outside the repo (team nickname, deadlines, spec rules) are now checked against the source before the agent writes code. The test now also checks the course's worked example (`bright-forest` → `211c220`) so the hashing method itself is verified, not only our own value.

**What worked:** we gave the agent the acceptance criteria from each issue as its spec, one story per branch. For the AI feature we asked for the failure cases first (no key, timeout, HTTP 402, malformed JSON, over the daily limit). The tests mock the HTTP call and also install a guard that fails any test that tries to reach the network.

**Review caught a bug the tests didn't:** Apoorve reviewed every pull request with his own AI agent, asking it to read each diff against the issue's acceptance criteria and to hold back anything that didn't match. It approved #12–#15 and **held #16**: if a player pressed `H` and the hint was still on its way when the run ended, the radio skipped the end-of-run request, so that run got no journal entry. All 13 radio tests passed because they test the server, not the timing in the browser. We fixed it in the same PR (the end-of-run request now waits its turn, and a run counter stops a late reply from landing on a restarted run) and reproduced the exact case in a browser with a slowed-down radio before re-requesting review. It also caught that the PR description overstated the test count (14 vs 13). **What we changed:** reviews are now done by a second agent with a different instruction ("find what doesn't match the spec") rather than the agent that wrote the code.

## Backlog changes for next sprint
- **New story: AI survival assistant** ([#11](https://github.com/pdchhaparwal/backrooms/issues/11)), labeled `user story`, in Sprint 2 and Sprint 3. Started this sprint; it carries over. The next slice is clues tied to the exit door ([#5](https://github.com/pdchhaparwal/backrooms/issues/5)): the radio hints at where the exit is without revealing it. After that, an evaluation set of situations run like tests
- Sprint 3 as planned: exit door [#5](https://github.com/pdchhaparwal/backrooms/issues/5), entity chases you [#6](https://github.com/pdchhaparwal/backrooms/issues/6), new layout every run [#7](https://github.com/pdchhaparwal/backrooms/issues/7)
- From review: edit [#2](https://github.com/pdchhaparwal/backrooms/issues/2) to describe the `production` branch + Promote action (it still says "tagged release"); exclude staff and `?v=`-forced sessions from the Play Now experiment; tie the run-length bound on saved runs to the real run length before the leaderboard (#10)
- Chores: make CI a required check on `main`; replace the remaining GitHub usernames on the A/B page with course nicknames; before the Sprint 4 A/B run, delete our own test impressions and clicks on production
- Carry over: nothing else (#2, #3, #4 closed)
