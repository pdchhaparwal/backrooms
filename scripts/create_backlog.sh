#!/usr/bin/env bash
# Creates the "user story" label and the backlog issues in the current GitHub repo.
# Needs the GitHub CLI: `brew install gh && gh auth login`. Run from the repo root:
#   ./scripts/create_backlog.sh
# Optional: also add each issue to the team Project board (needs `gh auth refresh -s project`):
#   PROJECT_OWNER=<user-or-org> PROJECT_NUMBER=<n> ./scripts/create_backlog.sh
set -euo pipefail

# Uses the REST API only. Repo defaults to the `origin` remote; override with REPO=owner/name.
REPO="${REPO:-$(git remote get-url origin | sed -E 's#.*github\.com[:/]##; s#\.git$##')}"
echo "repo: $REPO"

gh api "repos/$REPO/labels" -f name="user story" -f color="D4C66A" \
  -f description="User story for the backlog" >/dev/null 2>&1 || true   # already exists is fine

story() {
  local title="$1" body="$2" url
  url=$(gh api "repos/$REPO/issues" -f title="$title" -f body="$body" -f "labels[]=user story" --jq .html_url)
  echo "created: $url"
  if [[ -n "${PROJECT_NUMBER:-}" && -n "${PROJECT_OWNER:-}" ]]; then
    gh project item-add "$PROJECT_NUMBER" --owner "$PROJECT_OWNER" --url "$url" >/dev/null && echo "  added to project $PROJECT_NUMBER"
  fi
}

story "Walking skeleton: accounts, seed, A/B page, staging deploy" "$(cat <<'EOF'
As a grader, I want to log in to a deployed staging app and see the A/B test page working, so that I can confirm the team's pipeline works end to end before real features are built.

**Acceptance criteria**
- [ ] Sign up, log in and log out with Django auth, on a laptop and a phone-sized screen
- [ ] App uses Postgres through `DATABASE_URL`; settings and secrets come from env vars; listens on `$PORT`; logs to stdout
- [ ] `python manage.py seed` creates `admin@example.com`, `player1@example.com`, `player2@example.com`; running it twice causes no errors or duplicates
- [ ] `/ef88062` is public, returns 200, lists the team, and has exactly one `<button id="abtest">` reading `kudos` or `thanks`
- [ ] Each new visitor gets a random 50/50 variant kept in their session; one impression and at most one click per visitor, stored with timestamps
- [ ] `/ef88062/stats` returns JSON with a live `preferred` value
- [ ] Automated tests cover the counting rules and the seed command
- [ ] Deployed to staging and everything above works there
EOF
)"

story "Production environment deployed from main" "$(cat <<'EOF'
As the team, we want a production environment separate from staging, so that graders and players always see a stable build while we keep shipping to staging.

**Acceptance criteria**
- [ ] A second Render service and database for production, with its own secrets
- [ ] Staging deploys automatically on merge to `main`; production deploys on a tagged release
- [ ] Seed runs on both; the A/B page and stats work on both
EOF
)"

story "Save each run and show a personal best" "$(cat <<'EOF'
As a player, I want my runs saved, so that I can see whether I'm getting better.

**Acceptance criteria**
- [ ] When a run ends, time survived, distance walked, attacks, hits and whether the entity was banished are saved to the database for the logged-in player
- [ ] The Play Now page shows my last 5 runs and my best run
- [ ] A run can't be saved for another user (server uses the session user, not a form field)
EOF
)"

story "Measure which Play Now variant gets more players into the game" "$(cat <<'EOF'
As the team, we want to know which Play Now page design gets more people to start a run, so that we keep the better one.

**Acceptance criteria**
- [ ] Each Play Now view records the visitor's variant (A or B) once per session
- [ ] Starting a run records a conversion for that variant, at most once per session
- [ ] A staff-only page shows views, conversions and conversion rate per variant
EOF
)"

story "Find the exit to finish Level 0" "$(cat <<'EOF'
As a player, I want an exit door somewhere in Level 0, so that a run has a goal beyond surviving.

**Acceptance criteria**
- [ ] One exit tile per map, visible as a door on the wall
- [ ] Reaching it ends the run with "ESCAPED" and the time taken
- [ ] Runs are no longer capped at 5 seconds once the exit exists (cap becomes 120 s)
EOF
)"

story "Entity chases you and a catch ends the run" "$(cat <<'EOF'
As a player, I want the entity to hunt me around walls, so that the game has real tension.

**Acceptance criteria**
- [ ] Entity pathfinds around walls toward the player (no walking through walls)
- [ ] Being caught ends the run with "CAUGHT"
- [ ] Attacking stuns the entity for 2 seconds instead of removing it
EOF
)"

story "New Level 0 layout every run" "$(cat <<'EOF'
As a player, I want the hallways to change every run, so that I can't memorize the map.

**Acceptance criteria**
- [ ] Map is generated from a seed at run start; every open tile is reachable
- [ ] The seed is shown on the end screen and saved with the run, so a layout can be replayed
EOF
)"

story "Touch controls on a phone" "$(cat <<'EOF'
As a player on a phone, I want on-screen controls, so that I can play without a keyboard.

**Acceptance criteria**
- [ ] On touch devices, a D-pad and an attack button appear over the game
- [ ] The game canvas fits a 390px-wide screen without horizontal scrolling
EOF
)"

story "Reduced-flicker and sound settings" "$(cat <<'EOF'
As a player sensitive to flashing lights or noise, I want to turn off the flicker and the hum, so that I can play comfortably.

**Acceptance criteria**
- [ ] Settings page with "reduce flicker" and "sound on/off", saved per account
- [ ] The game respects both settings and the OS `prefers-reduced-motion` setting
EOF
)"

story "Leaderboard of fastest escapes" "$(cat <<'EOF'
As a player, I want to see the fastest escapes, so that I have something to beat.

**Acceptance criteria**
- [ ] Public leaderboard page with the top 10 escape times (username, time, date)
- [ ] Only completed escapes count; one entry per player (their best)
EOF
)"

echo "Done. Now assign each issue to its iteration on the Project board."
