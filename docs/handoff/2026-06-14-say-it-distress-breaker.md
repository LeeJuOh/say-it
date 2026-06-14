---
topic: say-it-distress-breaker
date: 2026-06-14
---

# say-it — distress circuit-breaker (issue 07)

This is the **say-it Claude Code skill** (`skills/say-it/SKILL.md`), built one
issue at a time through the local issue tracker (`docs/issues/`). The plugin *is*
the skill; each issue is a vertical slice. Issue 06 (S3/S4 wrap-up) just closed,
so the 4-stage arc now runs end to end. Next slice is the **distress
circuit-breaker** — the one safety feature this product cannot ship without.

## Goal

Implement `docs/issues/07-distress-breaker.md`: a **2-layer detection + 2-grade
response** distress breaker (ADR 0003). HARD layer = deterministic Korean-locale
keyword regex in the hook (unbypassable, fires every turn); SOFT layer = model
prompt-judgment for variants the regex can't catch. Grade 1 (panic) → model
de-escalates and wraps up; Grade 2 (acute self-harm) → model surfaces a Korean
crisis hotline AND the session is set **BLOCKED** so the hook refuses to resume it.
**Distress outranks everything** — the turn cap, stage transitions, the persona.

## First Action

Read `docs/issues/07-distress-breaker.md` (8-item acceptance list) and
`docs/adr/0003-safety-stop-hard-gate.md`. Then read the **distress seam already
wired through `scripts/sayit_state.py`**: `DISTRESS_PATTERNS` (line ~47, empty
list — this is what you populate), `check_distress()` (~184, already scans the
list and returns `{"triggered", "tier"}` with `tier ∈ {"panic","acute-harm"}`),
`evaluate_guards`/`tick` (already fold distress into the per-turn guard block), and
`render_reminder` (~297, already emits `distress guard: TRIGGERED tier=…`). The
call sites exist; issue 07 supplies the **patterns**, the **grade→render copy**,
and the **BLOCKED session state + resume gate**. Run `python3 -m unittest discover
-s tests` after. Consider `/tdd` — the false-positive boundary (below) is the
crux and is exactly what a red-test-first loop nails.

## Context

The whole arc (S1 vent → S2 role-swap → S3 integration → S4 closure) is live as of
issue 06. SKILL.md's "Reading the hook" section already tells the model that a
TRIGGERED distress guard overrides the stage and the persona (break character
instantly), and routes `panic → de-escalate`, `acute-harm → hotline, no resume` —
but **`DISTRESS_PATTERNS` is empty**, so nothing actually fires yet. The SOFT layer
is named as "your own judgment on top" but isn't fleshed into grade-specific render
copy. So today the breaker is all scaffold, no trigger. Issue 07 makes it bite.

**The tier naming bridge:** code uses `tier="panic"` / `tier="acute-harm"`; the
issue calls these **Grade 1** / **Grade 2**. Same thing — map panic↔GRADE_1,
acute-harm↔GRADE_2. `check_distress` already makes acute-harm outrank panic
(`TestDistressSeam.test_acute_harm_outranks_panic`), so the routing precedence is
done; you're filling the patterns and the response.

## The trap to design around (product-specific false positives)

This is the hard part and the reason a naive keyword list is *wrong* here. This
product's core use is the user **pouring out suppressed rage** — profanity, fury,
"I want to kill them" aimed at the *other person* is **normal catharsis** and must
NOT trigger. The discriminator is **direction**, not intensity:

- **Normal venting (must NOT fire):** "죽여버리고 싶어" (rage *at the persona*),
  "미쳐버리겠다", "때려치우고 싶다" — aimed at the other / the situation.
- **Grade 1 panic (fire, de-escalate):** "무서워", "너무 힘들어", "그만하고 싶어" —
  the user voicing *their own* distress.
- **Grade 2 acute harm (fire, hotline + BLOCK):** "죽고 싶어", "사라지고 싶어",
  자해 — directed at the *user themselves*.

A false positive cuts off legitimate catharsis = the product breaks. So the regex
must encode self-directed vs other-directed, not just match "죽" or "끝". The
acceptance list makes the false-positive test (normal venting stays clear) a
first-class requirement — write those negatives before the positives.

## Current Progress

Issues 01–04, **06** done and committed on `main`; tree clean. Recent commits:
- `2866115` docs(issues) — issue 06 → `done/`
- `281b554` feat(s3-s4) — integration + closure 4-bit wrap-up
- `9411e4a` docs(handoff) — (now-stale s3-s4 resume doc; kept for history)

Nothing started on issue 07. Its `Blocked by: 01` is long cleared.

## Decisions Made (locked — carried from 01–06, do not re-debate)

1. **State logic in `sayit_state.py`, CLI/shell thin.** Distress detection lives in
   `check_distress`; the hook (`scripts/tick.py`) only calls it. Keep regex +
   grade routing + BLOCKED transition in the tested library, not the hook script.
2. **Detection = hook (HARD, deterministic); enforcement render = model.** The
   model renders the de-escalation / hotline, but it acts on a *freshly injected*
   authoritative system-reminder, so it's not the model-goodwill dependence ADR
   0004 warns against — same pattern the stage/cap guards already use.
3. **Distress > turn cap > stage transition.** Already stated in SKILL.md; the code
   must honor it (a TRIGGERED distress guard ends the session regardless of turn
   count or stage).
4. **Hotline = duty-of-care, not therapy.** Surfacing a crisis line does **not**
   conflict with the "not therapy / light one round" frame — it's acknowledging a
   limit. Keep the framing intact.
5. **English source only.** Verify before finishing:
   `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` → 0. ⚠️ **This bites issue
   07 specifically:** the Korean keyword regexes are runtime *data*, not source
   prose — they must NOT sit as literal Hangul in `sayit_state.py`. Issue 06 hit a
   smaller version of this and resolved it by keeping test fixtures
   language-neutral (`"Señor Café"`, accented-Latin, passes the Hangul gate).
   Decide early where the Korean patterns live so the gate stays green — likely a
   **separate data file** (e.g. a JSON/text resource under the plugin) loaded by
   `sayit_state`, not inline string literals. Settle this before writing patterns.

## What Worked (reuse)

- **Close-out rhythm:** implement → `python3 -m unittest discover -s tests` →
  Hangul grep → throwaway `SAY_IT_DATA_DIR=$(mktemp -d)` end-to-end smoke →
  move issue to `docs/issues/done/` with a top-of-file blockquote closing note
  (impl hash + deviations) → **2 commits** (impl, then the docs move citing the
  impl hash). The 2-commit split keeps the done-note's hash stable.
- **Thin CLI / shell over a tested library helper** (the 01–06 split). For issue
  07, the new surfaces to unit-test are: regex true-positives, false-positives
  (normal venting stays clear), grade routing, and the BLOCKED resume gate.
- **CLI smoke in a mktemp dir** for any runtime path — issue 06 drove the full
  start→transition→save→end flow on disk before commit and caught behaviour end to
  end. Do the same for the distress path: trigger → grade reminder → BLOCKED →
  resume-refused.

## Blockers / open design questions (resolve at the top of issue 07)

1. **Where do the Korean patterns live?** (Decisions §5 ⚠️) — inline Hangul breaks
   the English-source gate. Pick a data-file home and a loader before writing them.
2. **BLOCKED is a new session concept.** `session_state.json` today has only
   `active` (bool); the hook gates on it (`scripts/tick.py`). Grade 2 needs a
   *blocked* state that (a) ends the current session and (b) makes the hook refuse
   to *resume* it later. Decide the field (e.g. a `blocked: true` / status enum on
   session_state) and add the resume-refusal branch to the hook + `session_start`.
   **Note:** this is the *session* BLOCKED, distinct from the *persona* `blocked`
   flag (issue 08, still a documented no-op in SKILL.md step 1) — don't conflate.

## Next Steps (after First Action)

1. Decide pattern-storage home (Blocker 1) + BLOCKED state shape (Blocker 2).
2. Populate the HARD layer: Korean regexes into the `DISTRESS_PATTERNS` mechanism,
   encoding self- vs other-directed so normal venting never fires.
3. Wire Grade 2: `render_reminder` injects `DISTRESS_GRADE_2` + Korean crisis
   hotline number, session goes BLOCKED; hook refuses resume on a BLOCKED session.
4. Wire Grade 1: `render_reminder` injects `DISTRESS_GRADE_1`; SKILL.md gains
   grade-specific render copy (Grade 1 de-escalate/wrap-up; Grade 2 hotline).
5. SKILL.md: extend "Reading the hook" with the grade-marker branches + the SOFT
   prompt layer for variant phrasings the regex misses.
6. Tests: true-positive, false-positive (normal catharsis stays clear), grade
   routing, BLOCKED resume-refusal. `/tdd`-friendly.
7. Close out per the rhythm above (2 commits, done-note with impl hash).

## Reference

- Issue: `docs/issues/07-distress-breaker.md`
- ADR: `docs/adr/0003-safety-stop-hard-gate.md` (the gate), `0004-state-tick-via-hook.md`
  (why fresh-injected reminders beat model memory)
- Edit targets: `scripts/sayit_state.py` (`DISTRESS_PATTERNS`, `check_distress`,
  `render_reminder`, session BLOCKED state), `scripts/tick.py` (resume gate),
  `skills/say-it/SKILL.md` ("Reading the hook" grade branches + render copy),
  `tests/test_state.py` (`TestDistressSeam` is the existing seam test to grow)
- Domain: `CONTEXT.md` (catharsis is the use case → false positives are fatal)
- Done: issues 01–04, 06 in `docs/issues/done/`. After 07: **09** (integration
  smoke = final eval). 08 (persona correction), 10 (safety disclosure) independent.
  Issue 05 is `merged → 03` (don't pick up).
