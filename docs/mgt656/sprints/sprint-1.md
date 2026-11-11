# Sprint 1 report: walking skeleton

## Sprint goal
Get the pipeline working end to end before building real features: a Django app with user accounts on Postgres, deployed to staging, with a seed command for grader accounts and the A/B test page. On top of the skeleton, a 5-second playable slice of the game proves the front end works.

## What shipped
- [Walking skeleton: accounts, seed, A/B page, staging deploy](TODO-link-to-issue-1)
  - Django 5.2 app with signup, login and logout
  - Settings and secrets in environment variables, Postgres through `DATABASE_URL`, logs to stdout, listens on `$PORT`
  - `python manage.py seed` creates `admin@example.com`, `player1@example.com` and `player2@example.com`; safe to run repeatedly; passwords come from environment variables, not git
  - A/B test page at `/ef88062` (first 7 characters of the SHA-1 of our team nickname `656-mba-backrooms`) and live JSON at `/ef88062/stats`
  - Two designs each for the login, Play Now and instructions pages (assigned per visitor; `?v=a` / `?v=b` to switch)
  - Playable 5-second Level 0 demo: WASD/arrows to move and turn, Space to attack, one entity, end screen listing which controls were tested
  - 24 automated tests (A/B counting rules, stats, seed, auth, page variants), passing against Postgres
- Backlog: 10 user stories with acceptance criteria (TODO-link-to-issues), labeled `user story`
- [Project board](TODO-link-to-project) with one iteration per sprint

## What works on staging now
Staging: TODO-staging-url (Render web service, Neon Postgres)
- Signup, login, logout; the three seeded accounts can log in
- Play Now → instructions → playable demo
- `/ef88062` shows one `kudos` or `thanks` button, assigned at random and kept per visitor, with one impression and at most one click counted per visitor
- `/ef88062/stats` returns JSON with a live `preferred` value

Not yet built: saved runs, exit/win condition, production environment (Sprint 2).

## Working with our AI agent
Unit tests passed, but they couldn't see layout. The agent also drove the app in a headless browser and took screenshots of every page variant. That caught a broken keycap layout on instructions variant B (the A key rendered on the top row next to W), which no test flagged. Second lesson: the A/B URL is a hash of the exact nickname string, so `656 MBA Backrooms` and `656-mba-backrooms` give different URLs (`/7a042f9` vs `/ef88062`). We confirmed the exact nickname instead of letting the agent guess, and pinned it with a test.

## Backlog changes for next sprint
- Sprint 2 candidates: production environment, saving runs with a personal best, and measuring which Play Now variant converts better
- Replace GitHub usernames on the A/B page with course nicknames if the course requires them
- Carry over: nothing
