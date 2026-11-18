# Component board

A separate, invite-only review app for Implicity's component intake. The pilot covers eight needs with three candidates each. All source and licence records are under `data/`; only captured images and clips ship as previews. Team approval is a deliberate owner status change informed by the votes, with no automatic majority rule.

## Run locally

Docker Desktop must be running. Generate local access values (keep them private):

```sh
mkdir -p .secrets
python3 - <<'PY'
import os, secrets
path = '.secrets/deployment.env'
if os.path.exists(path):
    raise SystemExit('Existing secrets retained; do not replace them to restart the board')
with open(path, 'w') as f:
    for key in ('INVITE_CODE', 'OWNER_CODE', 'SESSION_SECRET'):
        f.write(key + '=' + secrets.token_urlsafe(32) + '\n')
os.chmod(path, 0o600)
PY
docker compose up --build -d
```

Open `http://localhost:8088/?invite=<INVITE_CODE>`. Take the value from your private env file; do not paste it into issues or commit it. Use Owner in the navigation and enter OWNER_CODE to export, import, approve or delete all team data. The URL invite is exchanged for an HttpOnly, SameSite=Strict signed cookie, then removed from browser history. Invite and owner codes never appear in committed files. Session cookies contain an opaque person identifier, not an email. Changing an access code affects new exchanges; rotate SESSION_SECRET to invalidate all existing cookies. On Render cookies are Secure; local HTTP disables that flag explicitly.

Name and email are for review attribution, not verified identity. There are no passwords or account recovery. Keep the original browser cookies to edit votes. Re-entering the same email in a different browser is blocked rather than exposing its votes. An invite holder can submit another identity with a new email; this is a trusted-team review tool, not a secure election. The owner can export or delete all team data, including statuses, and deletion invalidates all sessions. Export files contain personal data; retain only as long as needed. JSON imports are limited to 4 MB for this small-team pilot.

Postgres's named volume persists through `docker compose down` and rebuilds. `docker compose down -v` destroys local reviews: export first. No API keys or production database URLs are needed for local runs.

## Pilot provenance and previews

`python3 scripts/shortlist.py` streams the read-only parent CSV with a raised field limit. The explicit pilot source pool is documented in `data/shortlist-run.json`; it is a deliberately bounded, source-verified sample, not a claim of exhaustively scoring 143k items. Item-level functional tags, React source, publisher-origin resolution, examples/marketing exclusions, paid/Pro exclusions, address/hash deduplication and verified repository licences are gates. Static rubric scores count concrete source indicators; they do not certify keyboard behaviour or complete states. MMR ranks the vetted pool using relevance and diversity of tags, dependency stack, interaction pattern and registry, with at most two from a registry per need. No popularity data is used.

`data/evidence/` stores registry snapshots and pinned repository licences, including hashes and commit links. Registry source revision is the exact fetched item JSON hash; the repository licence commit is recorded separately, without claiming that the live registry deployed that commit. Licence verification is root-repository evidence; per-component provenance must be rechecked before an actual port, including transitive copied components and npm licences.

Preview generation installs the captured registry snapshot with the shadcn CLI inside a fresh disposable container, with no host source, credentials or outside mounts. It has two CPUs, 3 GB RAM, a PID limit, no extra capabilities and process timeouts. Network is detached before rendering. Playwright also blocks non-local requests. Each fixture is a minimal usage of the actual upstream source, never a screenshot imitation. The Kibo code-block fixture pins react-icons 5.4.0 (newer icons removed SiCss3), and its table pins TanStack Table 8.21.3 (the registry source uses the v8 API); these compatibility overrides are explicit in fixtures.json and installed only in the sandbox. Images show upstream styling with a standard shadcn theme, not Implicity's eventual tokens.

```sh
python3 scripts/previews.py --build
# Re-run one failed/changed fixture:
python3 scripts/previews.py --id assistant-ui-elements-tool-call
```

Read `docs/signals.md` for data boundaries and `docs/deployment-decision.md` for free-tier expiry, restore and costs.

## Verify

```sh
python3 -m py_compile app.py scripts/shortlist.py scripts/previews.py
node --check static/app.js
# These tests intentionally use and clear a disposable LOCAL board:
python3 tests/api_smoke.py
sh tests/run-browser.sh
```

The browser smoke covers onboarding, eight-card batches, editable votes, skipping, come back later, owner approval, JSON export, included search, 1440/1024/768/390/320 widths and dark/reduced-motion. API smoke covers access boundaries, hidden totals, version binding, unique/editable votes, exports, atomic restore and session revocation. Do not point destructive smoke tests at a board with real votes.

## Render

Deploy `render.yaml` from this repository. Set INVITE_CODE, OWNER_CODE and SESSION_SECRET as secret environment variables, DATABASE_EXPIRES_AT to the actual date Render supplies (YYYY-MM-DD), and DATABASE_URL from the Blueprint database connection. The owner's chosen free tier costs $0 within quotas and its database expires after 30 days: export and rotate before expiry. Static previews survive redeploys in the image, and relational data stays in Postgres.

`scripts/render_deploy.py` is an optional API path for this provisioned workspace. It reads RENDERAPIKEY only from ignored `.env` and keeps receipts/connection details in ignored `.secrets/` with mode 600. It does not log secrets. After pushing a tested commit, request a deploy; auto-deploy is off so intermediate preview work is not published. Render access and billing decisions stay with the owner.

## Next wave

Supply a concrete needs list and desired review count. Run `python3 scripts/shortlist.py --wave wave-02 --config wave-02.json`, where the JSON has `needs` (each need has `tags` and source-vetted `items` addresses), `repositories` (namespace → GitHub owner/repo) and `signals` (need → arrays of event name, possible action and integration text). Other waves remain in the catalog. Add a new source-vetted pool, retain gate/evidence records, score and diversify it, write minimal fixtures, run the same isolated harness and verify signal event names against the current contract. Keep old component IDs; changing a registry snapshot hash creates a new voting version. Approval does not port a component: the eventual Implicity change still needs plain CSS tokens, reviewed props/events/data schemas, lazy loading, measured size, motion/accessibility checks, light/dark/theme/density render tests and a long-thread check.
