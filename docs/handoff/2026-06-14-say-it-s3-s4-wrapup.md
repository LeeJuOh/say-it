---
topic: say-it-s3-s4-wrapup
date: 2026-06-14
---

# say-it — S3 integration + S4 closure wrap-up (issue 06)

This is the **say-it Claude Code skill** (`skills/say-it/SKILL.md`), built one
issue at a time through the local issue tracker (`docs/issues/`), not through the
skill-creator-pro eval loop. The plugin *is* the skill; each issue is a vertical
slice of it.

## Goal

Implement `docs/issues/06-s3-s4-wrapup.md`: the **S3 integration** transition
("so what did I actually want?") and the **S4 closure 4-bit wrap-up** (takeaway
draft → user owns it in their own words → fiction reminder → label dedup + save →
warm-but-plain closing line), then force-close the session. This completes the
4-stage arc end to end and is the slice that makes issue 03's **entry revisit
gate actually bite** — that gate matches on saved labels, and nothing saves a
label until this lands.

## First Action

Read `docs/issues/06-s3-s4-wrapup.md` (9-item acceptance list), then read the
**Close step** of `skills/say-it/SKILL.md` (lifecycle step 5, ~line 155, plus the
S2 role-swap module just above it) — it already scaffolds the
`save_takeaway.py` + `session_end.py` calls this slice fills in. Then add an
**S3 (integration)** + **S4 (closure, 4 bits)** facilitation module to SKILL.md,
matching the voice of the existing S1/S2 modules. This slice is **mostly
prompt-layer** — the scripts it needs already exist (see Context) — so resist
adding new Python; wire the modules to the seams that are there. Run
`python3 -m unittest discover -s tests` after.

## Context

Issues 01, 02, 03, **04** are done and committed on `main`; working tree clean,
HEAD `9f77d86`. The session arc can now *move* (issue 04 just landed the
`transition_stage.sh` motor), but it has no S3/S4 facilitation, so a session
reaching `integration` has nothing to run. Issue 06 is that content.

**Every script seam this issue needs already exists** — issue 06 is wiring, not
plumbing:

- `scripts/save_takeaway.py --persona <id> --theme "<label>" --takeaway "<raw>"`
  — appends RAW to `takeaway_log.json` (append-only, unit-tested in
  `TestTakeawayLog`). This is the "save_takeaway.sh 또는 동등 스크립트" the issue
  names; the repo's is `.py`. **Do not create a new save script** — use this one.
- `scripts/session_end.py` — flips `active=false`, the forced close.
- `scripts/transition_stage.sh integration` then `… closure` — the motor carries
  S2→S3→S4 (forward-only; landed in issue 04).
- `sayit_state.load_log(dd)` — list prior entries to show existing labels for
  dedup. `sayit_state.find_revisit(dd, persona, theme)` — **exact-string** match
  for reuse.

**The label-matching distinction is the trap to not fall into** (it already bit
issue 03 once): the **S4 exit dedup** here is **exact-string** `find_revisit` (a
script/deterministic match — same `(persona, theme)` ⇒ reuse the label). The
**S1 entry revisit gate** is **semantic model judgment** over the log's theme
labels. Different tools, different layers — don't reach for `find_revisit` at the
entry gate, and don't make the exit dedup a fuzzy model call.

**The delicate part is the closing-line tone (bit 5).** Warm but plain, not
clinical "saved. done," and not heavy therapy-speak ("you're doing so well"). You
put down *this one knot*, never *the person* — they're alive, the user sees them
tomorrow ("set this knot down" ⭕ / "said goodbye to them" ❌). Keep the "light one
round" frame. The issue cites the ex-skill `/let-go` tone as reference.

## Current Progress

Issues 01–04 done and committed on `main`; tree clean. Recent commits:
- `9f77d86` docs(issues) — issue 04 → `done/`
- `cd6311c` feat(turn-cap) — stage-transition motor + vent turn cap
- `3521d89` feat(s1-vent) — S1 vent + S2 role-swap (prompt-only)

Nothing started on issue 06. Its `Blocked by: 03` is long cleared.

## Decisions Made (locked — carried from 01–04, do not re-debate)

1. **State logic in `sayit_state.py`, CLI/shell thin.** But note: issue 06 likely
   adds **no new Python** — its scripts exist. Acceptance §"save_takeaway 유닛테스트"
   is already largely covered by `TestTakeawayLog` (append correctness + raw
   preservation); add a CLI-level smoke test only if you judge the existing
   coverage thin.
2. **Compare at the door, save on the way out.** The `theme_label` is assigned and
   saved at **closure** (bit 4), null until then. `session_start.py` deliberately
   passes no `--theme`.
3. **Takeaway stored RAW** — no summarizing/compression, so same-issue similarity
   stays accurate (the S4 dedup and the S1 entry gate both depend on it).
4. **Forced close on one takeaway line.** Don't let closure run on into
   between-session rumination — `session_end.py` right after the save.
5. **Exit dedup = exact string (`find_revisit`); entry gate = semantic judgment.**
   See Context. This is the one correction issue 03 had to make; don't repeat it.
6. **Distress (issue 07) outranks everything**, closure included. Already in
   SKILL.md "Reading the hook."
7. **English source only.** Verify before finishing:
   `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` → 0.

## What Worked (reuse)

- **Tight close-out rhythm:** implement → `python3 -m unittest discover -s tests`
  → Hangul grep → move issue to `docs/issues/done/` with a closing note (impl
  hash + deviations) → **2 commits** (impl, then the docs move citing the impl
  hash). The 2-commit split keeps the done-note's hash stable.
- **Throwaway `SAY_IT_DATA_DIR=$(mktemp -d)` smoke tests** for any runtime
  invocation (CLI + hook). Issue 04 used this to drive the full
  start→tick→cap→transition flow on disk and caught the behaviour end to end
  before commit — do the same for the closure save + forced-end path.
- **Thin CLI / shell over a tested library helper** — kept logic unit-testable
  across 01–04. Issue 06 mostly *consumes* that; honor it if you do touch a script.

## Next Steps (after First Action)

1. SKILL.md **S3 integration** module: the user returns to their own chair, the
   prompt shifts rumination → problem-solving ("so what did I actually want from
   them?"). Reached via `transition_stage.sh integration`.
2. SKILL.md **S4 closure** module, the 4 bits + closing line (issue 06 §closure):
   draft takeaway → user re-articulates in their own words (not a bare "yeah") →
   fiction reminder (cognitive defusion) → label dedup (`load_log`/`find_revisit`,
   exact match) + `save_takeaway.py` → warm-but-plain close. Then `session_end.py`.
3. Tests: confirm `TestTakeawayLog` covers acceptance §"append 정확성/JSON 무결성";
   add a `save_takeaway.py` CLI smoke test if coverage feels thin.
4. Close out: move `docs/issues/06-s3-s4-wrapup.md` → `docs/issues/done/` with a
   closing note (impl hash + deviations), per `docs/agents/issue-tracker.md`.
5. Note in the done-note that this slice **activates issue 03's entry revisit
   gate** (labels now exist to match against).

## Reference

- Issue: `docs/issues/06-s3-s4-wrapup.md`
- Edit target: `skills/say-it/SKILL.md` (S3 + S4 modules; lifecycle step 5 already
  scaffolds the Close calls). Likely no new scripts.
- Existing seams: `scripts/save_takeaway.py`, `scripts/session_end.py`,
  `scripts/transition_stage.sh` (issue 04), `sayit_state.load_log` /
  `find_revisit` / `append_takeaway`
- Domain: `CONTEXT.md` ("compare at the door, save on the way out"; put down the
  knot not the person; light one round, not therapy); the issue cites `/let-go`
  tone for the closing line
- Done: issues 01–04 in `docs/issues/done/`. Prior handoff (issue 04):
  `docs/handoff/2026-06-14-say-it-turn-cap.md` (now stale — issue 04 closed; kept
  for history)
- After 06: **07** (distress keywords — fills the `DISTRESS_PATTERNS` seam),
  then 09 (integration smoke = final eval). 08, 10 independent. Issue 05 is
  `merged → 03` (already absorbed — don't pick it up).
