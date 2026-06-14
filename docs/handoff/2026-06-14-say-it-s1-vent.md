---
topic: say-it-s1-vent
date: 2026-06-14
---

# say-it — S1 vent + revisit-guard entry + S2 scaffolding (issue 03)

## Goal

Implement `docs/issues/03-s1-vent.md`: turn the `/say-it` SKILL.md from a draft
contract into the actual **session runner**. Entry (persona selection + revisit
guard), S1 vent (bot renders the persona in *receiving mode*), and the S2
role-swap *entry scaffolding* (full S2 lands in issue 05). This is the
critical-path slice that unblocks the S1→S4 chain.

## First Action

Read these three, then start editing `skills/say-it/SKILL.md` (it already exists
as a draft contract — extend it, don't rewrite from zero):

1. `docs/issues/03-s1-vent.md` — the acceptance list (10 items).
2. `skills/say-it/SKILL.md` — current draft: session-lifecycle + hook contract
   already specified; you're adding the S1/S2 facilitation + entry logic.
3. `skills/say-it-build/SKILL.md` — the sibling builder, for voice/structure to
   match (just shipped in issue 02).

This slice is **mostly prompt work in one file** — see Decisions for why almost
no Python is needed.

## Context

Issues 01 (hook/state infra) and 02 (persona builder) are **done and committed**.
Everything issue 03 reads already exists; the work is SKILL.md prompt modules plus
wiring to helpers that are already written:

- Persona selection → `list_personas(dd)` / `load_persona(dd, id)` in
  `scripts/sayit_state.py` (added in issue 02). 0 personas → point at
  `/say-it-build`; 1 → start; 2+ → "who do you want to sit across from?".
- Session already activates via `scripts/session_start.py --persona <id>`; the
  hook (`scripts/tick.py`) then ticks every turn and injects the authoritative
  `<system-reminder>` carrying `stage`/`turn`/guards. The runner **reads** stage
  from that block, never counts turns itself (the contract is already documented
  in the draft SKILL.md "Reading the hook" section).
- The bot renderer is a prompt module: respond *as* the persona using its L1–L4
  layers and L0 hard rules. The whole point of L0 (built in issue 02) is to stop
  the bot breaking character into a fake apology/comfort — lean on it.

## Current Progress

Working tree clean, all committed. On `main`. Recent commits:
- `62c639c` feat(persona-builder) — `/say-it-build`, persona write path, 34 tests
- `7f2cc16` docs(issues) — issue 02 → `docs/issues/done/`

Nothing started on issue 03 yet. Issue 03's `Blocked by:` (01, 02) is now cleared.

## Decisions Made (locked — do not re-debate)

1. **Entry revisit matching = MODEL judgment (semantic), NOT exact string.** At S1
   entry the model compares the user's opening against the existing theme labels in
   `takeaway_log.json` semantically and asks a reflection question on a match. The
   exact-string `find_revisit()` helper is for the S4 *exit* dedup (issue 06) —
   don't wire it into entry. (⚠️ `docs/issues/03-s1-vent.md` lines 20–21, CONTEXT.md
   "비교는 입구에서, 저장은 출구에서".)
2. **First session = entry check is a no-op.** Empty `takeaway_log` → pass straight
   to S1. This is what makes issue 03 testable standalone; the guard only really
   fires once issue 06 has saved a label+takeaway.
3. **Revisit guard output is a reflection question, NOT a block** (CONTEXT.md). Same
   persona + *different* theme = a legitimately different issue = pass through, never
   exile.
4. **S2 here is entry SCAFFOLDING only.** The full role-swap joins in issue 05. Build
   the invitation/guidance ("if they were here, what would they say?") and the
   graceful no-pressure exit when the user resists — not the full S2 loop.
5. **ADR 0001 (S2): the USER voices the other person, the bot does not.** The bot
   never advocates/defends the other side — the knot only sets if the perspective
   comes from the user's own mouth.
6. **English source only** (carried from 01/02). All SKILL.md prose English; Korean
   appears only as runtime persona *data*. Verify before finishing:
   `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` → 0.

## What Worked (reuse)

- **Slice = one SKILL.md + thin helpers, logic in `sayit_state.py`.** Issues 01/02
  kept all state logic in `sayit_state.py` (unit-testable, stdlib-only) and made
  CLIs/skills thin. Issue 03 likely needs **no** new Python — if you find yourself
  writing state logic, put it in `sayit_state.py` with a test, not in the skill.
- **Tight close-out rhythm:** implement → run `python3 -m unittest discover -s tests`
  → Hangul grep → move issue to `docs/issues/done/` with a closing note → 2 commits
  (impl, then the docs move referencing the impl hash). The 2-commit split avoids
  the amend hash-drift problem (the done-note must cite a stable hash).

## Open Questions (resolve early, don't block on)

- **"BLOCKED status" persona handling** (issue 03 line 8, acceptance line 43): the
  issue wants a "blocked" notice path, but no BLOCKED state exists in the persona
  schema or `sayit_state.py` yet (persona correction = issue 08). Clarify with the
  user whether issue 03 should introduce a minimal blocked flag or just stub the
  branch and defer. Likely: stub/defer, since 08 owns corrections.

## Next Steps (after First Action)

Distilled from the issue 03 acceptance list (full text in the issue):

1. **Entry logic** in `/say-it` SKILL.md: persona selection (0 / 1 / 2+ via
   `list_personas`), then the semantic revisit-guard entry check (no-op on empty
   log), then start the session (`session_start.py --persona <id>`).
2. **S1 bot renderer** prompt module: respond as the persona from its layers,
   *receiving mode* (absorb the vent, no counter-attack/escalation), edges + L0 held
   so it never goes suddenly-nice.
3. **S2 entry scaffolding** prompt module: the role-swap invitation + guidance, and
   graceful encouragement (not coercion) if the user resists. Mark clearly that the
   full S2 loop is issue 05.
4. **Tests**: entry selection + the standalone-testable no-op revisit path can be
   exercised via `sayit_state` helpers if you add any logic there; the renderer
   itself is prompt-level (human/eval review, not unit-test).
5. **Close out**: move `docs/issues/03-s1-vent.md` → `docs/issues/done/` with a
   closing note (impl commit hash + any deviations), per
   `docs/agents/issue-tracker.md`.

## Reference

- Issue: `docs/issues/03-s1-vent.md`
- Runner skill (edit target): `skills/say-it/SKILL.md`
- Helpers already in place: `scripts/sayit_state.py`
  (`list_personas`/`load_persona`/`find_revisit`/`render_reminder`),
  `scripts/session_start.py`, `scripts/session_end.py`
- Domain: `CONTEXT.md` (revisit guard, issue = (persona, theme), "비교는 입구에서,
  저장은 출구에서"); ADR 0001 (S2 user voices the other)
- Done: issues 01, 02 in `docs/issues/done/`. Prior handoff for 02:
  `docs/handoff/2026-06-13-say-it-persona-builder.md`
- After 03: 05 (full S2), 06 (S3/S4 + exit dedup, where the revisit guard becomes
  live); 04, 07, 10 independent; 09 = final human eval.
