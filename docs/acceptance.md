# Component board acceptance

Completed 2026-11-18 in this separate repository. Runtime release: `cf2693e1755ec9d9399be21062c151868a84f795`.

Live site: https://component-board.onrender.com
Repository: https://github.com/6DEADSHOT9/Component-Board
Render web service: `srv-dbuq8qm8bjmc739k24s0`; database: `dpg-dbuq5eijnfac73e0ol2g-a`; accepted deployment: `dep-dbuqmoo8v5cc739tfaig`.

The private invite URL was delivered to the coordinator. INVITE_CODE, OWNER_CODE and SESSION_SECRET are Render secret environment variables; the generated values are also in ignored `.secrets/deployment.env`, mode 600. The Render API credential stays in ignored `.env` as RENDERAPIKEY. No credentials or invite URL are committed. Use the Owner navigation and OWNER_CODE for results, status changes, JSON/CSV export, JSON restore and delete-all.

## Pilot

Streamed 143,254 catalog records. The pilot is a bounded, source-verified selection, not an exhaustive quality assessment of the entire index. The reproducible gates, source hashes, repository revisions, licence evidence, static rubric and MMR method are recorded in `data/shortlist-run.json`, `data/candidates.json` and `data/evidence/`.

Each need has three candidates: AI chat pieces; prompt input; code block; data table; chart; files and attachments; command palette and search; toast and inline feedback. There are 24 candidates from five registries, at most two from a registry within a need. All have verified MIT or Apache-2.0 repository licence evidence and event-contract signal mappings with integration requirements. Dice's command stack was excluded for unresolved registry packaging; see `data/rejected.json`.

The isolated harness produced 48 light/dark images, 20 interaction images and 20 short clips. Installs run in fresh Docker containers without secrets or host mounts, with resource/time limits; network is detached before rendering. The browser blocks outside requests too. Actual upstream source is rendered in minimal fixtures through Vite, React and Tailwind; the board itself serves static images/video and uses plain CSS. Bundle estimates compare production JS/CSS gzip output against an empty React harness; they are upstream preview cost, not a claimed size for a future Implicity port. Compatibility pins for two Kibo fixtures are documented in the README.

## Checks passed

- Python compilation, JavaScript syntax and `git diff --check`.
- Provenance hashes, 24 unique candidates, eight needs, licence gates and the per-registry diversity cap.
- API onboarding and access isolation, one editable vote per component version, hidden totals, stale-version rejection, version-bound approval and owner-only actions.
- Full JSON/CSV export, spreadsheet formula neutralization, transactional JSON restore, stale approval handling and session revocation after delete-all.
- Browser onboarding, eight-card batches, Yes/No edits, Skip, come back later, owner approval, export and included-component search.
- Responsive widths 1440, 1024, 768, 390 and 320; dark mode and reduced motion; all 48 light/dark images loaded and visually inspected.
- Exact local Postgres participant/vote/status snapshot and reviewer session continuity through web and database restarts.
- Owner-only expiry reminder seven days before database expiry.
- Exact participant/vote snapshot survived the actual Render redeploy from the initial release to `cf2693e`.
- Live invite exchange, onboarding, voting, owner export, all 24 complete preview records, browser owner access/search, JSON/CSV export, mobile layout and browser-origin request acceptance.

Synthetic live acceptance data was deleted. The team starts with zero participants and no votes or approvals. Included stays empty until the owner marks reviewed components approved.

## Cost, retention and next wave

The owner chose free Render web and free Render Postgres: **$0 within free-tier quotas**. The database expires **2026-12-18 at 13:06 UTC**; export before then and recreate/restore as documented in `docs/deployment-decision.md`. The owner reminder begins December 11. The free server sleeps after idle and may take about a minute to wake. Local Docker's named Postgres volume persists without a scheduled expiry.

The next wave needs a concrete needs list, source-vetted addresses and repositories, and signal/integration mappings. `scripts/shortlist.py --wave wave-02 --config wave-02.json` retains other waves and reuses the same gates, fixtures and capture pipeline. Instructions and config shape are in the README.

Real-device touch and screen-reader checks were not performed. Static accessibility/state rubric indicators are not accessibility certification, and repository licence evidence must be rechecked with dependency provenance before an actual port. No component has been adopted into Implicity; adoption still needs its token port, reviewed schemas, lazy loading, measured port size, theme/density and long-thread checks.
