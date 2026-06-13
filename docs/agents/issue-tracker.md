# Issue tracker: Local Markdown

Issues for this repo live as markdown files in `docs/issues/`.

## Conventions

- Issues are `docs/issues/<NN>-<slug>.md`, numbered from `01`
- PRD is `docs/prd/PRD.md`
- Triage state is recorded as a `Status:` line at the top of each issue file (see `triage-labels.md` for the role strings)
- Dependencies are recorded as a `Blocked by:` line below Status
- **Completed issues move to `docs/issues/done/<NN>-<slug>.md`** once implemented and committed, so the top of `docs/issues/` shows only outstanding work. Keep a closing note in the file (commit hash + any intentional deviations). `Blocked by:` lines reference the `<NN>-<slug>` stem, not a path, so the move doesn't break them.

## When a skill says "publish to the issue tracker"

Create a new file under `docs/issues/`.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.
