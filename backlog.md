# Backlog

Engineering backlog — items to pick up later. Newest first.

---

## ops-monitor: don't fail (red + alert) for pages that are merged but not yet deployed

**Priority:** Medium · **Area:** ops / CI · **Opened:** 2026-08-16 · **Status:** quick-win SHIPPED; robust gating still open

### Shipped 2026-08-16 (mitigation + foundation)
- **Pre-flight skip (quick-win)** — `ops/robot_customer/robot.spec.js`: `PENDING_DEPLOY` allow-list
  (env `OPS_PENDING_DEPLOY`, default `/en/marriage-v3,/hi/marriage-v3`) + `skipIfPendingDeploy()`
  called at the top of B1/B2/B3. A listed route that 404s on the live target is **skipped**, not
  failed; once it returns 200 (deployed) it's tested normally (self-heals). Any UN-listed route that
  404s still fails hard. → marriage-v3 no longer reds the monitor while undeployed.
- **`/healthz {version}` (foundation for robust gating)** — `api.py` `_app_version()` reads
  `APP_COMMIT` / `GIT_SHA` / `GIT_COMMIT` env or a `.git-sha` file; `/healthz` now returns
  `{"status":"ok","version":"<sha>"}` (still `status:"ok"`, non-breaking).

### Still open (the robust version)
Replace the manual `PENDING_DEPLOY` allow-list with **deployed-SHA gating**: have the deploy stamp
`APP_COMMIT` (or write `.git-sha`), then in the robot read `/healthz {version}` and run a feature's
tests only when its introducing commit is an ancestor of the live SHA. Removes the manual list upkeep.
**Blocked on:** the deploy actually setting `APP_COMMIT` / writing `.git-sha` (deploy-process change).

### Problem
The `ops-monitor` workflow (Phase B — robot customer smoke test, `ops/robot_customer/robot.spec.js`)
runs against the **live site** (`OPS_TARGET_URL`), but its list of pages to test is coupled to the
**merged code** on `aws-mysql`. When a new page is merged before it is deployed, the robot tests the
new URL, gets a `404` from the live site, and turns the whole monitor **red** — firing a critical
email + WhatsApp alert on every scheduled run (06:00 / 14:00 / 22:00 IST).

### Incident that surfaced it (2026-08-15/16)
- PR #74 merged `marriage-v3` (pages `marriage-v3.html` + `.hi.html`, routes `/en/marriage-v3` and
  `/hi/marriage-v3`) **and** the robot tests that assert those pages.
- Production was not deployed with #74, so live `/en/marriage-v3` + `/hi/marriage-v3` returned `404`.
- Robot result: **106 passed, 12 failed** — all 12 were marriage-v3 (B1 page-health, B2 funnel, B3 SEO,
  × EN/HI × mobile/desktop). Site was fully healthy; it was a false alarm.
- No customer impact; auto-rollback stayed disarmed (`OPS_ROLLBACK_ARMED` blank).

### Root cause
Test coverage is keyed off "is it in the code" (merge), while the monitor checks "is it on the live
site" (deploy). The two drift whenever a page is merged ahead of its deploy.

### Desired behaviour
A page that is merged-but-not-yet-live should be treated as **pending deploy** (skip + informational
note), NOT a critical failure — while a page that **was** live and has regressed to 404 must still
fail hard (real outage).

### Options (pick during grooming)
1. **Live-availability pre-flight (quick win).** Before the marriage-v3 / any "new" block runs, do a
   cheap `GET` on the target path; if it 404s AND the path is on an allow-list of "not-yet-released"
   routes, `test.skip()` with a "pending deploy" annotation instead of failing. Downside: an
   allow-list must be curated, and a genuinely-missing page could be masked if mis-listed.
2. **Deployed-version awareness (most robust).** Expose the deployed git SHA on the live site
   (e.g. extend `/healthz` to return `version`/`commit`). The robot only runs a feature's tests when
   that feature's introducing SHA is an ancestor of the live SHA. New pages auto-covered exactly when
   they go live; regressions still fail. Requires a version endpoint + build-time SHA injection.
3. **Released-pages manifest.** Keep a `LIVE_PAGES` list (config or env the deploy updates). The robot
   iterates only released pages; adding a page to the manifest is part of the deploy step, not the
   merge. Simple, but relies on deploy discipline to update the manifest.
4. **Process guard (no code).** Only merge a page's robot tests in the same change that deploys it, or
   land new-page tests behind a feature flag. Weakest — human ordering, easy to forget.

**Recommended:** (2) if a version endpoint is cheap to add; otherwise (1) as an immediate mitigation,
layered so "was-live-now-404" still fails hard.

### Acceptance criteria
- Merging a new landing page ahead of its deploy leaves `ops-monitor` **green** (with a visible
  "pending deploy: /en/foo" note), and sends **no critical alert**.
- A page that was previously live and starts returning 404/5xx still turns the monitor **red** and alerts.
- No change to the auto-rollback safety (stays disarmed unless explicitly armed).

### Related
- `.github/workflows/ops-monitor.yml` (Phase B), `ops/robot_customer/robot.spec.js`
  (`PAGES` list ~L47-48, marriage-v3 block ~L223-224), `ops/watcher.py`, `ops/config.py`.
