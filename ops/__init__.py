"""ops — the T6 monitoring & auto-recovery framework ("three bots").

Self-contained: it watches a running deployment from the OUTSIDE (over HTTP,
like a real customer / a monitor would), so it barely touches the main app and
never depends on the app's internals. Three bots:

  watcher.py         — the heartbeat: health + (later) resource-balance checks
  robot_customer/    — the "real user": drives the live site end to end
  mechanic.py        — the responder: rollback + recover + alert on failure

Shared plumbing:
  config.py          — all settings from env (portable, secret-free)
  alerts.py          — email (reliable) + WhatsApp (best-effort) notifications

Everything is env-driven, so the same kit can watch local, staging, or prod by
changing OPS_TARGET_URL. Nothing here runs automatically until wired into the
GitHub Actions workflows under .github/workflows/.
"""
