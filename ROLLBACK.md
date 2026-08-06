# Roll back to any saved version (Elastic Beanstalk)

Elastic Beanstalk keeps every deployed version's bundle in AWS storage (S3). These
two GitHub Actions let you redeploy **any** of them — including several versions
back, for the case where a bug has been live across the last few deploys.

**No new setup:** the AWS keycard secrets (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`) already exist (the deploy job uses them). The IAM user
needs `elasticbeanstalk:DescribeApplicationVersions`, `DescribeEnvironments`, and
`UpdateEnvironment` — it already has UpdateEnvironment from deploys; if a run
fails on a permission error, Deepak adds the two Describe permissions.

## How to roll back (2 clicks)

1. **See the saved versions.** GitHub → **Actions → "eb-list-versions" → Run
   workflow.** The log prints the currently-live version and the last 25 saved
   versions (newest first: Version label, date, description). Pick the label you
   want (e.g., the one from before the bug appeared).

2. **Roll back to it.** GitHub → **Actions → "eb-rollback" → Run workflow.**
   - `version_label`: paste the exact label from step 1.
   - `confirm_env`: type `AxtroShastraProd` (a safety guard).
   Run it. It records the current live version, checks your chosen version
   exists, deploys it, and waits for the environment to go **Green**, then prints
   the new live version.

## Notes
- This is **Method B** — it redeploys the chosen bundle to the single server, so
  there's a brief blip during the swap (seconds–minute). No extra server, no cost.
- To undo a rollback, just run `eb-rollback` again with the previous label (the
  workflow prints it before switching).
- Retention: EB keeps a history of versions; if you ever can't find an old
  version, its lifecycle policy may have pruned it (`eb appversion` shows the
  list / limit).
