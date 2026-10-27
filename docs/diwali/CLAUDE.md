# Rules for working on the Diwali report

- Never read `diwali_bank.py` (repo root) whole. It is very large. Search it
  (grep for the key, function or phrase you need) or read only the line range you need.
- Agent cost rule: every Workflow `agent()` call and every Agent-tool spawn for this
  project uses `model: 'sonnet'`; mechanical steps (running tests, grep checks,
  screenshots) also use `effort: 'low'`. Use the session model only when the user
  asks for it for a specific step.
