---
topic: say-it-persona-correction
date: 2026-06-20
---

# say-it — last two slices: persona correction (08) + final integration eval (09)

This is the **say-it Claude Code plugin** (`skills/say-it` runner + `skills/say-it-build`
builder), built one issue at a time through the local tracker (`docs/issues/`). Each
issue is a vertical slice. **Issue 10 (user safety disclosure) just closed** — the
static safety layer is live. Only two slices remain before the MVP is complete:

- **Issue 08 — persona correction** (`ready-for-agent`, dep 03 done): agent-implementable. *Recommended next.*
- **Issue 09 — integration smoke eval** (`ready-for-human`, all deps now clear): the
  capstone human walkthrough + subjective sign-off.

Do **08 first**: it's the last *impl* slice, and 09 should eval the *complete*
product (including the correction flow), not one missing it.

## Goal

Implement `docs/issues/08-persona-correction.md`: when the user says "그 사람 안 이래"
(that's not how they are) during/after a session, **append a correction to the
persona as a non-destructive layer** — original data preserved, corrections
accumulate across sessions so the persona drifts toward the user's perception over
time. It is `/say-it` SKILL.md guidance + the `corrections` array the build already
seeds empty.

## First Action

Read `docs/issues/08-persona-correction.md` (4-item acceptance), then read the
persona's `corrections` seam as it already exists: `grep -n "corrections" scripts/sayit_state.py
skills/say-it-build/SKILL.md skills/say-it/references/schemas/persona.schema.json`.
The build already writes `corrections: []` (say-it-build SKILL.md "Write the persona"),
so 08 is **append-to-an-existing-array + a save helper + SKILL.md trigger guidance**,
not a schema change. Recommend `/tdd` — this is deterministic state logic
(append-correction, persistence, original preserved) with three code-checkable
acceptance items; write the failing test first, mirror the existing
`save_takeaway.py` / `append_takeaway` pattern in `sayit_state.py`.

## Context

The whole arc is live and committed: persona build (`/say-it-build`) → S1 vent → S2
role-swap → S3 integration → S4 closure, with the turn cap, revisit guard, distress
circuit-breaker, and (as of 10) the static safety notice all in place. Issue 08 is
the one *content-quality* loop left: closing the gap between the built persona and
the user's actual perception via post-session correction. It's independent of 09 but
should land first so 09 evals the finished product.

The `corrections` array has been a documented-but-empty seam since issue 01's schema
and issue 02's builder ("start it empty here" — say-it-build SKILL.md). 08 is where
it finally gets written to. Key design constraint from the issue: **non-destructive
layering** — never overwrite L1–L4; stack corrections with enough trace (what/when/why)
to see how the persona evolved.

## Current Progress

Issues 01–04, 06, 07, **10** done and committed on `main`; tree clean. Issue 10's
three commits (newest first):
- `bd51907` refactor(safety) — strip dev jargon from the user-facing SAFETY.md
- `f2bcd14` docs(issues) — issue 10 → `done/`
- `85d0860` feat(safety) — disclosure one-pager + build-entry notice + `hotline_text()`

Nothing started on 08 or 09. Issue 05 is `merged → 03` — **do not pick up.**

## Decisions Made (locked — carried 01–10, do not re-debate)

1. **State logic in `sayit_state.py`; CLI/shell thin.** 08 adds an append helper here
   (mirror `append_takeaway`) + a `scripts/` CLI wrapper (mirror `save_takeaway.py`),
   the model calls it the way it calls the other save scripts.
2. **English source only; Korean lives as runtime data, never as source prose.** The
   gate enforces it (see ⚠️ below). The user's correction text is *runtime data*
   (stored as-is, `ensure_ascii=False`), same as persona layers and takeaways.
3. **Non-destructive correction layering** (issue 08): corrections append to the
   `corrections` array, original L1–L4 untouched. Preserve provenance per correction.
4. **Issue 09 is human-driven** (`ready-for-human`): the tone/edges/scaffolding/closure
   quality is subjective → needs the user to role-play sessions across the
   relation×emotion×vent-volume matrix and sign off. An agent can *set up* the eval
   matrix and drive the mechanical checks, but not self-certify the subjective ones.

## What Worked (reuse)

- **Close-out rhythm:** implement → `python3 -m unittest discover -s tests` →
  Hangul gate (`grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` = 0) →
  throwaway `SAY_IT_DATA_DIR=$(mktemp -d)` end-to-end smoke → move issue to
  `docs/issues/done/` with a top blockquote done-note (impl hash + intentional
  deviations) → **2 commits** (impl, then docs move citing the impl hash). The split
  keeps the done-note's cited hash stable — **don't `--amend` the impl commit after
  the docs commit cites it** (that's why issue 10's polish went in a *third* commit
  `bd51907`, not an amend).
- **Single-source helper pattern:** issue 10 added `sayit_state.hotline_text()` as the
  one place the lexicon hotline becomes user-facing text, shared by three call sites,
  killing two duplicated formatters. When a value must not drift across surfaces, give
  it one rendering function and route everyone through it.
- **Audience split for docs:** mechanism/agent prose and user-facing prose are
  *different files*, not different sections (SAFETY.md = user; distress-detection.md =
  agent). Dev provenance (ADR refs, code paths) in a user doc goes in a trailing
  `<!-- source notes -->` HTML comment, so the model renders clean prose to the user
  but a maintainer reading raw still sees the trail.
- **`/tdd` fit:** 08's acceptance is mostly code-checkable (trigger, persisted,
  original preserved) — a good TDD slice, unlike 09 (subjective).

## What Didn't Work / traps (adjust, don't repeat)

1. ⚠️ **The Hangul gate is easy to trip from your own comments.** Twice during issue
   10 I wrote Korean (`불일치 금지`) into `scripts/sayit_state.py` and `tests/test_state.py`
   docstrings/comments and broke the gate. **Any** Hangul under `scripts/skills/tests`
   fails it — including code comments. Keep Korean in `docs/` or `lexicon/` only; in
   source, write the rationale in English (e.g. "no-mismatch rule", not "불일치 금지").
   Run the gate as the *last* check before committing, every time.
2. ⚠️ **`git mv` + unstaged edits = stale commit.** I edited a file (done-note +
   checkboxes), then `git mv`'d it; `git mv` staged the *index* blob (pre-edit), and
   the commit captured the stale content while my edits sat unstaged at the new path.
   Fix was a follow-up `git add <newpath> && git commit --amend`. If you edit a file
   you're about to move, `git add` it explicitly after the move and check `git diff`
   is empty before committing.

## Blockers / open questions

- **08:** none. Self-contained; `corrections` seam already exists.
- **09:** needs the human in the loop for the subjective sign-off and the session
  walkthroughs — can't be fully closed by an agent alone.
- **No open design call for 08 — the correction-entry shape is already pinned** by
  `persona.schema.json`: `items.required: ["at", "layer", "note"]`, with `layer` an
  enum of `L0_hard_rules`/`L1_identity`/`L2_voice`/`L3_emotional_triggers`/`L4_relationship_dynamics`,
  plus optional `from`/`to` (before/after) strings. **Conform to this**, don't invent
  field names. One thing to confirm: `sayit_state.py`'s persona validator (~line 562)
  currently only checks `corrections` is a *list*, not per-item shape — decide in 08
  whether the new append helper validates each entry against the schema or trusts the
  caller (mirror how `append_takeaway` handles it).

## Next Steps (after First Action)

1. Implement 08: append-correction helper in `sayit_state.py` (+ `scripts/` CLI
   wrapper), SKILL.md trigger guidance for detecting "그 사람 안 이래" mid/post-session,
   non-destructive layering. Close out per the rhythm (tests, Hangul gate, smoke,
   2 commits, done-note).
2. Then **09 — final integration eval** (the MVP capstone): set up the eval matrix
   (relation × emotion × vent-volume, per the issue), drive a full
   build→S1→S2→S3→S4 walkthrough, verify the build-entry safety notice fires once and
   all three guards trip correctly, and get the human's subjective sign-off on tone.
   This is the last issue; closing it completes the MVP.

## Reference

- Issues: `docs/issues/08-persona-correction.md`, `docs/issues/09-integration-smoke.md`
- Prior slice (just closed): `docs/issues/done/10-safety-disclosure.md` (done-note),
  and the previous handoff `docs/handoff/2026-06-20-say-it-safety-disclosure.md`
- Patterns to mirror for 08: `scripts/save_takeaway.py` + `sayit_state.append_takeaway`
  (CLI-wraps-state-helper), persona write path in `skills/say-it-build/SKILL.md`
- Schema: `skills/say-it/references/schemas/persona.schema.json` (the `corrections` field)
- Domain glossary: `CONTEXT.md`; sequence is the issue tracker (`docs/agents/issue-tracker.md`)
