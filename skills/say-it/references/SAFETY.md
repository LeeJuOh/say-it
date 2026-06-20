# Safety — distress circuit-breaker

> **Status: HARD floor live (issue 07).** The deterministic detection floor, the
> two-grade response, and the BLOCKED resume-refusal are implemented. What issue
> **[10](../../../docs/issues/10-safety-disclosure.md)** still owns is the *user-facing*
> safety disclosure/notice wording (the up-front "this is not therapy" notice and
> the consent/limits copy) — not the runtime detection, which lives here now.

## Why a hard floor exists (ADR 0003)

Safety detection is two-layered, and the split is deliberate
([ADR 0003](../../../docs/adr/0003-safety-stop-hard-gate.md)):

- **HARD floor** — code-level regex in `scripts/sayit_state.py`
  (`check_distress` / `DISTRESS_PATTERNS`). Runs every turn on the hook, fires on
  obvious signals unconditionally, and the model cannot talk its way past it. A
  prompt-only safety net is forbidden, because a long conversation can drift the
  model off its instructions exactly when it matters most.
- **SOFT augment** — prompt-level guidance layered *on top of* the floor for
  variation and context (`SKILL.md` → "Reading the hook"). It strengthens the
  floor; it never replaces it.

## Where the Korean detection data lives

The keyword regexes and the crisis-hotline resource are locale-specific *runtime
data*, not source prose, so they sit in a JSON lexicon **outside** the
English-source tree (`scripts/skills/tests` stay Hangul-free; the gate
`grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` must be 0):

- `lexicon/distress.ko.json` — the patterns (each `(regex, tier)` with an English
  note explaining the self-vs-other rationale) plus the crisis hotline. This is the
  single source issue 10's disclosure copy shares — do not duplicate the number.
- `lexicon/distress_examples.ko.json` — the labelled corpus the unit tests assert
  against (true-positives, and the all-important false-positives).

`sayit_state.load_distress_lexicon()` loads both globals (`DISTRESS_PATTERNS`,
`DISTRESS_HOTLINE`) once at import.

## The false-positive constraint (this product's specific trap)

This product's core use is the user pouring out suppressed rage. Profanity, fury,
"I want to kill them" aimed at the *other person* is **normal catharsis** and must
NOT trigger the breaker — cutting off legitimate venting is how the product breaks.
So the floor discriminates on **direction**, not intensity: outward rage stays
clear; the user's own self-directed distress fires. The patterns encode this (e.g.
the desiderative "want to die" fires, but the transitive "want to kill them" does
not), and the corpus locks it down with negatives written first.

## The two grades

When the breaker triggers, the session stops immediately, ahead of the turn cap and
the stage:

1. **panic (Grade 1)** — the user's own acute distress → the hook injects
   `DISTRESS_TRIGGERED: GRADE_1`; the model breaks character, de-escalates, and
   winds the session down (soft landing, not a takeaway closure).
2. **acute-harm (Grade 2)** — self-harm / crisis signals → the hook injects
   `DISTRESS_TRIGGERED: GRADE_2` plus the crisis hotline, and **latches the session
   BLOCKED in code** (`tick` sets `blocked=true`, `active=false`). The model surfaces
   the hotline verbatim. Resume is refused two ways: the tick hook re-injects a
   safety hold every later turn, and `session_start.py` refuses to open a new round.
   The SOFT layer can reach the same latch via `session_block.py` for acute signals
   the regex missed.

Surfacing a crisis line is duty-of-care, not therapy: it acknowledges a limit
("not our domain — here") and so does **not** conflict with the "not therapy, light
one round" frame (ADR 0003 — regulatorily, it is evidence of care).

## What issue 10 ([10-safety-disclosure](../../../docs/issues/10-safety-disclosure.md)) still owns

- The up-front user-facing safety notice / disclosure copy (the "not therapy" frame,
  limits, consent), which references — does not re-define — the hotline number here.
- Any future locale or jurisdiction handling for the crisis resources (not planned;
  this product is Korean-locale by ADR 0003).
