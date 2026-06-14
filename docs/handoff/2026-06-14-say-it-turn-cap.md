---
topic: say-it-turn-cap
date: 2026-06-14
---

# say-it — stage transition + turn-cap (issue 04)

## Goal

Implement `docs/issues/04-turn-cap.md`: the **stage-transition mechanism**
(`scripts/transition_stage.sh`, forward-only) and the **vent-stage turn cap**
(8 soft → +3 one-time extension → 11 hard ceiling), enforced deterministically by
the hook with the invitation copy living in the SKILL.md prompt layer. This is the
slice that makes the session actually *move* — issue 03 wrote the S1/S2 prompt
modules but the session is currently frozen at `stage: vent` because nothing can
advance the stage value yet.

## First Action

Read `docs/issues/04-turn-cap.md` (9-item acceptance list), then create
`scripts/transition_stage.sh` as a thin CLI over a new `advance_stage(dd, next)`
helper you add to `scripts/sayit_state.py` (NOT logic in the shell script — keep
state logic in the library so it's unit-testable, the pattern issues 01–03 held).
Forward-only over `STAGES = ("vent","role-swap","integration","closure")` (already
defined in `sayit_state.py:35`); reject backward moves, skips, and unknown stage
names. Then add a `tests/` case. Run with `python3 -m unittest discover -s tests`.

## Context

Issues 01, 02, 03 are **done and committed** on `main`; working tree clean. The
runner (`skills/say-it/SKILL.md`) already *expects* this slice: its lifecycle
step 4 names `scripts/transition_stage.sh` as issue 04's, and the S2 role-swap
module only fires once something flips `stage` to `role-swap`. So issue 04 is the
missing motor, not new surface area — wire it to seams that already exist.

The cap is **half-built already** and just needs gating + extension + distinct
markers:

- `sayit_state.evaluate_guards()` already computes `turn_cap.soft_hit` /
  `hard_hit` as `turn >= soft` / `turn >= hard` (defaults `DEFAULT_SOFT_CAP=8`,
  `DEFAULT_HARD_CAP=11`, `sayit_state.py:39-40`). **But it is NOT stage-gated** —
  acceptance says the cap counts *only in vent*. Gate it so role-swap/integration/
  closure never trip it.
- `session_state` carries an unused `extension_used: False` field
  (`new_session`, `sayit_state.py:134`). That's the one-time +3 latch — wire it.
- `render_reminder()` already emits human cap lines (`sayit_state.py:242-247`).
  Issue 04 §"Hook 통신" wants explicit `CAP_TRIGGERED: SOFT` / `CAP_TRIGGERED: HARD`
  tokens in the injected reminder so the model can branch (SOFT → invite; HARD →
  force `transition_stage.sh`). Add those markers; keep them vent-only.

The extension math: soft 8 = gentle nudge ("we've let that out — move on?"); if the
user wants more, the one-time +3 carries them toward the hard ceiling 11; 11 = forced
close. `extension_used` makes "exactly once per session" enforceable in code, not
prompt.

## Current Progress

Working tree clean, all committed, on `main`. Recent commits:
- `62b2f77` docs(issues) — issue 03 → `done/`
- `3521d89` feat(s1-vent) — `/say-it` runner: S1 vent + S2 role-swap (prompt-only)

Nothing started on issue 04. Its only `Blocked by:` (01) is long cleared.

## Decisions Made (locked — do not re-debate)

1. **State logic in `sayit_state.py`, CLI/shell thin.** `transition_stage.sh` is a
   thin wrapper; the forward-only validation + write goes in an `advance_stage`
   helper with a unit test. Same split issues 01–03 used (`session_start.py` etc.
   are all thin over the library).
2. **Cap enforcement = hook (deterministic); signal interpretation = prompt.** The
   hook flags 8/11 by turn count; *reading* whether the user is winding down
   (repetition, dropping intensity, giving-up language) and choosing to invite
   onward is the model's job, never the script's (acceptance §9).
3. **Cap is vent-only.** role-swap/integration/closure are structured stages — no
   cap. Gate the existing `soft_hit`/`hard_hit` computation on `stage == "vent"`.
4. **Cap copy = invitation, not exile.** "We've let that out — want to move to the
   next chair?" never "stop." The whole product fights re-suppression; a curt cap
   would re-inflict it (issue 04 §캡 발동 문구).
5. **Distress (issue 07) outranks the cap.** If the distress guard is TRIGGERED,
   stop immediately regardless of cap state. The precedence is already documented
   in SKILL.md "Reading the hook"; just don't let cap logic override it.
6. **English source only** (carried from 01–03). Verify before finishing:
   `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` → 0.

## What Worked (reuse)

- **Thin CLI / shell over a tested library helper.** Every prior slice kept the
  decision logic in `sayit_state.py` (stdlib-only, unit-tested) and made the
  invocation surface dumb. `transition_stage.sh` should follow suit — the shell
  just parses one arg and calls Python.
- **Verify embedded one-liners before shipping.** Issue 03's SKILL.md calls a
  couple of `python3 -c` helpers; running them against a throwaway
  `SAY_IT_DATA_DIR=$(mktemp -d)` (empty + seeded) caught that they behave (no-op vs
  populated) before commit. Do the same for any new runtime invocation.
- **Tight close-out rhythm:** implement → `python3 -m unittest discover -s tests`
  → Hangul grep → move issue to `docs/issues/done/` with a closing note → **2
  commits** (impl, then the docs move citing the impl hash). The 2-commit split
  keeps the done-note's hash stable (no amend hash-drift).

## Open Questions (resolve early, don't block on)

- **Where does `transition_stage.sh` read the data dir?** The other CLIs use
  `sayit_state.data_dir()` (honors `SAY_IT_DATA_DIR` → `CLAUDE_PLUGIN_DATA`). Reuse
  it; don't hardcode a path. A bare `.sh` still needs to shell out to Python (or be
  a `.py` — the issue says `.sh`, but the repo's existing CLIs are `.py`; a `.sh`
  that just `exec python3 -c "...advance_stage..."` is fine and matches the named
  filename. Pick the `.sh`-named-but-calls-Python route to satisfy acceptance §1
  literally without putting logic in shell).
- **Does `transition_stage.sh` need to reset the turn counter on entering a new
  stage?** Cap is vent-only, so turns in later stages don't matter for the cap, but
  decide whether `turn` keeps climbing or resets per stage. Leaning: leave `turn`
  monotonic (the hook owns it) and just gate the cap on stage — simplest, no new
  coupling. Confirm against issue 06's needs before committing to it.

## Next Steps (after First Action)

1. `advance_stage(dd, next_stage)` in `sayit_state.py` + `transition_stage.sh`
   wrapper; forward-only, reject backward/skip/unknown. Unit tests (acceptance §2).
2. Stage-gate the cap: `soft_hit`/`hard_hit` (and the new `CAP_TRIGGERED` markers)
   only when `stage == "vent"`. Wire `extension_used` as the one-time +3 latch.
   Unit tests for 8-turn trigger, single extension, 11-turn force (acceptance §8).
3. Emit `CAP_TRIGGERED: SOFT|HARD` in `render_reminder()` (vent-only) so the model
   can branch.
4. SKILL.md: add a cap-reminder interpretation + invitation-copy module to
   `skills/say-it/SKILL.md` (acceptance §"SKILL.md 영향"). SOFT → invite onward;
   user accepts → `transition_stage.sh role-swap` (or extend once); HARD → force the
   transition. Keep the copy as invitation, not exile.
5. Close out: move `docs/issues/04-turn-cap.md` → `docs/issues/done/` with a closing
   note (impl hash + deviations), per `docs/agents/issue-tracker.md`.

## Reference

- Issue: `docs/issues/04-turn-cap.md`
- Edit targets: `scripts/sayit_state.py` (add `advance_stage`, stage-gate cap),
  new `scripts/transition_stage.sh`, `skills/say-it/SKILL.md` (cap module),
  `tests/` (transition + cap)
- Existing seams: `STAGES` (sayit_state.py:35), `evaluate_guards`/`tick`
  (`:202`/`:220`), `extension_used` (`:134`), `render_reminder` cap lines
  (`:242-247`), `DEFAULT_SOFT_CAP`/`DEFAULT_HARD_CAP` (`:39-40`)
- Domain: `CONTEXT.md` (turn cap = anti-rumination, distinct from distress
  circuit-breaker; cap = invitation not block); ADR 0004 (state tick via hook)
- Done: issues 01, 02, 03 in `docs/issues/done/`. Prior handoff (issue 03):
  `docs/handoff/2026-06-14-say-it-s1-vent.md`
- After 04: **06** (S3/S4 + exit dedup — where the revisit guard goes live and the
  Close-step `save_takeaway`/`session_end` contract gets its facilitation), then 07
  (distress keywords), 09 (integration smoke). 08, 10 independent; 09 = final eval.
  Issue 05 is `merged → 03` (already absorbed — don't pick it up).
