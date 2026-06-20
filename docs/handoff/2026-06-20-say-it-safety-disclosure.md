---
topic: say-it-safety-disclosure
date: 2026-06-20
---

# say-it — user safety disclosure (issue 10)

This is the **say-it Claude Code plugin** (`skills/say-it` runner + `skills/say-it-build`
builder), built one issue at a time through the local tracker (`docs/issues/`). The
plugin *is* the skills; each issue is a vertical slice. Issue 07 (distress
circuit-breaker) just closed, so the runtime safety floor is live. Next slice is
**issue 10 — the user-facing safety disclosure**, the last blocker before the final
integration eval (issue 09).

## Goal

Implement `docs/issues/10-safety-disclosure.md`: a **single user-facing safety
notice** that collects the already-decided safety elements (not therapy / "the
person as you perceive them" / crisis hotline / narration-only + local data /
living-people-only scope) into **one page**, and **surfaces a 1-time core notice at
`/say-it-build` entry**. This is a **"collect and surface, don't decide" slice** —
the substance is already settled and scattered across the PRD/ADRs/issues; you are
aggregating it, not setting new policy.

## First Action

Read `docs/issues/10-safety-disclosure.md` (7-item acceptance list), then read
`skills/say-it/references/SAFETY.md` **as it stands now** — and resolve the
ownership clash before writing anything: issue 07 **rewrote SAFETY.md into a
detection-*mechanism* reference** (agent-facing: HARD floor, grades, BLOCKED latch,
where the lexicon lives), but issue 10 expects `SAFETY.md` to be the **user-facing
one-pager**. They are different audiences in one filename. Decide the split first
(recommendation below), because everything else hangs off it. Consider `/grill-with-docs`
to pin the SAFETY.md structure against CONTEXT.md before coding — the two traps
below are exactly the kind of terminology/ownership snags it surfaces.

## Context

The whole arc is live: persona build (`/say-it-build`) → S1 vent → S2 role-swap →
S3 integration → S4 closure, with the turn cap, revisit guard, and (as of 07) the
distress circuit-breaker all enforcing. Issue 10 adds the **static** safety layer on
top of the **runtime** one: 07's distress path *surfaces the hotline dynamically when
a signal fires*; issue 10 is the *always-visible up-front notice* a user sees before
they ever start. Same safety story, two surfacing modes — don't conflate them.

## The two traps to design around (both already solved once, in 07)

1. **SAFETY.md ownership clash.** 07 made `skills/say-it/references/SAFETY.md` a
   *mechanism* doc. 10 wants it as the *user notice*. **Recommended split:** make
   `SAFETY.md` the user-facing one-pager (issue 10's deliverable), and move 07's
   detection-mechanism prose to a sibling like `references/distress-detection.md`
   (update the 3-4 inbound links: SKILL.md "Reading the hook", the SAFETY.md
   pointers, ADR/issue refs). Clean audience separation beats one file serving two
   readers. Confirm with the user if unsure — it touches a committed file.

2. **The Hangul gate vs a Korean user-facing notice.** ⚠️ The notice is *shown to
   Korean users*, so its natural language is Korean — but `SAFETY.md` sits under
   `skills/`, which the English-source gate scans
   (`grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` must stay **0**). A
   Korean SAFETY.md breaks the gate. This is the **exact** problem issue 07 hit with
   the keyword lexicon. Same two fixes apply — pick one early:
   - **(a) English source, model-renders-Korean** (matches how the persona voice and
     all session facilitation already work — SKILL.md is English, the model speaks
     Korean to the user at runtime). SAFETY.md stays English substance; the
     build-entry notice is rendered to the user in Korean by the model.
   - **(b) Korean notice as a data file outside the gated tree** (e.g.
     `lexicon/safety_notice.ko.md`), surfaced verbatim — the literal-data path 07
     used for the lexicon.
   (a) keeps it consistent with the rest of the product and is the lighter touch;
   lean that way unless verbatim legal-ish wording is wanted.

## Current Progress

Issues 01–04, 06, **07** done and committed on `main`; tree clean. Recent commits:
- `c1a0722` docs(issues) — issue 07 → `done/`
- `961e823` feat(distress) — 2-layer detection + 2-grade breaker (issue 07 impl)

Nothing started on issue 10. Its only dependency note (hotline shares 07's source) is
now satisfiable — see Decisions §3.

## Decisions Made (locked — carried 01–07, do not re-debate)

1. **State logic in `sayit_state.py`; CLI/shell thin.** (No new runtime state is
   likely needed for 10 — it's mostly SKILL.md prose + a bundled notice.)
2. **English source only; Korean lives as runtime data, never as source prose.**
   The gate enforces it. This is Trap 2 — settle the notice's language home first.
3. **Hotline `109` (자살예방 상담전화) is the single source, in
   `lexicon/distress.ko.json` (`DISTRESS_HOTLINE`).** Issue 10's notice must *share*
   this number, not re-declare it — acceptance says 불일치 금지. A static notice that
   hardcodes a second copy risks drift; cite it with a pointer to the lexicon (or
   have the model pull `st.DISTRESS_HOTLINE` when rendering).
4. **SAFETY, not COMPLIANCE.** Our risk is *emotional* safety (narration-only keeps
   data risk small), so the page is a safety notice, not a data-compliance contract.
   Structure can mirror ex-skill `COMPLIANCE.md` (data handling / allowed-forbidden
   uses / mental-health warning).
5. **Hotline coexists with "not therapy."** Surfacing a crisis line is duty-of-care
   (acknowledging a limit), not therapy — state this coexistence explicitly (ADR 0003).
6. **ToS / PIPA / server storage are out of scope** (hosting-app stage). This slice
   is a *notice/disclaimer/guide page*, not a contract.

## What Worked (reuse)

- **Close-out rhythm:** implement → `python3 -m unittest discover -s tests` →
  Hangul grep (`grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` = 0) →
  throwaway `SAY_IT_DATA_DIR=$(mktemp -d)` end-to-end smoke → move issue to
  `docs/issues/done/` with a top blockquote done-note (impl hash + intentional
  deviations) → **2 commits** (impl, then the docs move citing the impl hash). The
  split keeps the done-note's hash stable.
- **Korean-runtime-data pattern (07):** Korean lives in a data file *outside*
  `scripts/skills/tests`; English loader + English notes; tests load the data so the
  test source stays Hangul-free. Reuse verbatim if you pick Trap-2 option (b).
- **Negatives first** when a false-positive boundary is the crux (07's corpus).

## Blockers / open questions (resolve at the top of issue 10)

1. **SAFETY.md ownership** (Trap 1) — pick the split before writing.
2. **Notice language home** (Trap 2) — English-source+model-render vs Korean data
   file. Gate stays green either way only if decided up front.
3. **Build-entry surfacing point.** The 1-time core notice fires at `/say-it-build`
   entry → it lives in `skills/say-it-build/SKILL.md` (that skill exists). Decide the
   exact trigger spot (very first step, before any persona narration is requested).

## Next Steps (after First Action)

1. Resolve the 3 blockers above (SAFETY.md split, notice language, build-entry spot).
2. Write the one-page notice content: not-therapy / limits / crisis hotline / data
   (narration-only + local) / appropriate + forbidden uses / target scope
   (living people, no deceased, no minors). Hotline from the single source (§3).
3. Wire the 1-time core notice at `/say-it-build` entry (not therapy + "the person
   as you perceive them" + "if it gets hard, here's the hotline").
4. Keep `/say-it` session access to the static notice (the dynamic hotline is already
   07's runtime path — don't duplicate that mechanism).
5. Close out per the rhythm (Hangul gate, tests still green, 2 commits, done-note).

## Reference

- Issue: `docs/issues/10-safety-disclosure.md` (the "collect from these sources" table)
- Sources to aggregate: PRD (`docs/prd/PRD.md` — frame, scope), ADR
  [0002](../adr/0002-narration-only-input.md) (narration-only), ADR
  [0003](../adr/0003-safety-stop-hard-gate.md) (hotline, acute-harm stop)
- Edit targets: `skills/say-it/references/SAFETY.md` (split per Trap 1),
  `skills/say-it-build/SKILL.md` (build-entry notice), maybe `skills/say-it/SKILL.md`
  (in-session access + fix inbound links if SAFETY.md is split)
- Hotline source: `lexicon/distress.ko.json` → `DISTRESS_HOTLINE` (number `109`)
- Domain: `CONTEXT.md` (catharsis use case; SAFETY vs COMPLIANCE naming)
- Sequence: **10 next → then 09** (integration smoke / final human eval — its
  `Blocked by` list is now all-clear except 10). **08** (persona correction) is
  independent and can be picked anytime. Issue 05 is `merged → 03` (don't pick up).
