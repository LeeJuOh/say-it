---
topic: say-it-persona-builder
date: 2026-06-13
---

# say-it — Persona builder (issue 02)

## Goal

Implement `docs/issues/02-persona-builder.md`: a **separate** `/say-it-build`
skill that interviews the user and writes a 5-layer persona file
(`<data_dir>/personas/<id>.json`) conforming to issue 01's schema. Build and
session are deliberately separate mental models — `/say-it-build` builds the
persona; `/say-it` (issues 03+) runs the session against it.

## First Action

Read the spec and the output contract, then start the skill draft:

1. `docs/issues/02-persona-builder.md` — the full acceptance list.
2. `skills/say-it/references/schemas/persona.schema.json` — the exact output shape.
3. `scripts/sayit_state.py` — the persona contract already exists in code:
   `validate_persona()` (5 layers, **L4 `ambivalence` required**, `corrections`
   array), `persona_template()` (a minimal valid example), `_persona_path()`
   (`<data_dir>/personas/<id>.json`), `data_dir()` resolution.

Sanity-check the target shape before writing anything:

```bash
cd /Users/ljo/Desktop/project/zero-code/say-it
python3 -c "import sys; sys.path.insert(0,'scripts'); import sayit_state as st; \
print('errors:', st.validate_persona(st.persona_template()))"
# expect: errors: []
```

Then create `skills/say-it-build/SKILL.md` — the 5-layer intake flow. Build to
the schema; don't invent a new persona shape.

## Context

Issue 01 (hook/state infra) is **done and committed** — the deterministic
foundation `/say-it` runs on. Issue 02 is the first unblocked build issue (the
critical-path item: it gates the whole S1→S4 chain via issue 03). Everything
issue 02 needs to *write* a persona already exists in `scripts/sayit_state.py`;
the work is the skill (intake flow + inference rules + preview), not new state
plumbing — with one likely small addition (a `save_persona` helper, see Next
Steps).

## Current Progress

Working tree clean, all committed. Relevant commits:
- `aaa1d8a` feat(hook-infra) — state lib, schemas, hook, SKILL.md draft, 28 tests
- `316d6d7` docs(issues) — issue 01 moved to `docs/issues/done/`

What issue 02 builds on (already in place):
| Asset | Path | Use |
|---|---|---|
| persona schema | `skills/say-it/references/schemas/persona.schema.json` | output shape |
| `validate_persona()` | `scripts/sayit_state.py` | structural check before save |
| `persona_template()` | `scripts/sayit_state.py` | minimal valid example (English placeholders) |
| `_persona_path()` | `scripts/sayit_state.py` | `<data_dir>/personas/<id>.json` |
| conflict vocabulary | `skills/say-it/references/conflict-vocabulary.md` | label→behavior translator (English) |

## Decisions Made (locked — do not re-debate)

1. **English implementation, Korean only as runtime data.** ALL plugin source
   (SKILL.md, scripts, schemas, references docs) is English. Korean appears only
   as runtime *data*: the user's narration captured into persona layers, stored
   with `ensure_ascii=False`. The bot performs Korean at runtime from each
   persona's L2 voice — never hardcode Korean samples/dialogue in source. Verify
   before finishing: `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` → 0.
   (This overrides the older hook-infra handoff, which had a Korean-exception the
   user rejected.)
2. **Narration-only input** (ADR 0002, permanent): the user describes the person
   in their own words. **No KakaoTalk/chat-log upload.**
3. **Blank-field inference = extrapolate along the grain of the user's
   narration.** No demographic / zodiac / MBTI stereotypes — this is "the person
   *as I perceive them*," not "the average member of their job." (ex-skill's
   zodiac/MBTI fill-in is NOT carried over.)
4. **L4 ambivalence is required and preserved**, not smoothed. The person's own
   behavioral contradiction ("cold, then occasionally looks out for me") is the
   rumination engine, so it is a core field. `validate_persona` already enforces
   its presence.
5. **References bundle lives under the skill** (`skills/<skill>/references/`),
   not repo root. Root `./references` is a gitignored symlink to local reference
   projects — never write plugin files through it.

## Next Steps (after First Action)

Distilled from the issue 02 acceptance list — full text in the issue:

1. **Intake flow** — one pass of questions per layer (L0–L4). Include the
   negative-space question **"what would this person never say/do, even at their
   worst?"** → fills L0 hard rules (blocks the bot from a sudden fake
   apology/comfort; immersion + safety). Fallback: reverse-infer L0 from the
   narration if the user draws a blank.
2. **Use the conflict vocabulary as a translator** — map the user's vague label
   to concrete L2/L3/L4 behavior. It's a fallback, not a classification jail;
   the user's own words rank first. (Issue 02 wants it bundled in the *build*
   skill's `references/` — decide: share the single copy in
   `skills/say-it/references/`, or also place one under `skills/say-it-build/`.
   Prefer one source if the loader allows.)
3. **Preview before confirm** — show the persona summary, mark which layers are
   **narrated vs inferred** (use the `provenance` field), let the user correct
   the inferred parts, and show the "this is the person *as you perceive them*,
   not the real person" framing.
4. **Write the file** — validated persona to `<data_dir>/personas/<id>.json`,
   `id` = relationship+name slug (e.g. `boss-kim`). Multi-persona = multiple
   files in `personas/`. **Likely small addition to `scripts/sayit_state.py`:** a
   `save_persona(dd, persona)` that runs `validate_persona` then writes via the
   existing `_write_json_atomic` — there is no persona-write helper yet, only the
   path + validator. Add it there (single source of truth) rather than writing
   JSON from the skill.
5. **Tests** — extend `tests/test_state.py` (or a sibling) for any new helper
   (`save_persona` round-trip + rejects invalid). Run `python3 -m unittest
   discover -s tests`.
6. **Close out** — move `docs/issues/02-persona-builder.md` to
   `docs/issues/done/` with a closing note (commit hash + deviations), per the
   `done/` convention now documented in `docs/agents/issue-tracker.md`.

## Reference

- Issue: `docs/issues/02-persona-builder.md`
- Output contract: `skills/say-it/references/schemas/persona.schema.json`,
  `scripts/sayit_state.py` (`validate_persona`, `persona_template`)
- Domain: `CONTEXT.md` (persona, ambivalence, relationship context); ADR 0002
  (narration-only)
- Issue 01 (done): `docs/issues/done/01-hook-infra.md`
- Remaining after 02: 03 (S1+S2, blocked by 02) → 06/08 (blocked by 03); 04, 07,
  10 are independent of 02; 09 = final human eval.
