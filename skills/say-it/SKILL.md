---
name: say-it
description: >-
  Run an empty-chair session: let the user say the things they never got to say
  to a real person who still lives in their head (a boss, parent, partner,
  friend), then help them put that one knot down. Use this whenever the user
  wants to vent at or confront someone from their life, replay an argument they
  keep looping on, "finally say it" to someone, or work through unresolved
  feelings about a specific person — even if they don't name "empty chair" or
  "session." This is the session RUNNER; building the persona first is
  /say-it-build. Not therapy or counseling — a light, one-round ritual with
  guardrails against rumination.
---

# say-it — empty-chair session runner

This skill runs one structured empty-chair session against a persona the user
already built with `/say-it-build`. The session has four stages and is held on
the rails by a per-turn hook and three state files. This file is the **draft
contract** for issue 01 (the hook/state infrastructure slice): it specifies how
to read the hook's injected state and how to drive the session lifecycle. The
full stage-by-stage facilitation prompts are filled in by later slices (S1 vent
= issue 03, S2 role-swap = issue 05, S3/S4 integration+closure = issue 06).

## The session arc (4 stages)

`vent` → `role-swap` → `integration` → `closure`. The user's `stage` is owned by
the state file, not by your read of the conversation — see the contract below.

| stage | what happens | filled in by |
|---|---|---|
| `vent` (S1) | the persona shows up in their own voice and *receives* what the user pours out | issue 03 |
| `role-swap` (S2) | the user sits in the other chair and voices the other person themselves | issue 05 |
| `integration` (S3) | the user returns to their own seat: "so what did I actually want?" | issue 06 |
| `closure` (S4) | takeaway draft → user owns it in their words → fiction reminder → save label+takeaway | issue 06 |

## Reading the hook (the system-reminder contract)

A `UserPromptSubmit` hook (`scripts/tick.py`, ADR 0004) fires on **every** user
turn while a session is active and injects a `<system-reminder>` block that
starts with `[say-it session — authoritative state, refreshed this turn ...]`.
It carries `persona`, `stage`, `turn`, `theme`, the turn-cap status, and the
distress-guard status.

Treat that block as **authoritative and machine-owned**:

- Read `stage` from it to know which stage you are facilitating. Do not infer the
  stage from the conversation — a long vent can make you mis-judge where you are;
  the hook can't.
- Read `turn` and the turn-cap line from it. Do not count turns yourself.
- The reminder is freshly injected every turn, so it never goes stale the way an
  early system prompt does in a long session (the context-rot failure ADR 0004
  exists to prevent).
- If the distress guard is **TRIGGERED**, stop the session immediately and follow
  the safety path — `panic` → de-escalate and wrap up; `acute-harm` → surface the
  crisis hotline and do not resume (ADR 0003). This overrides whatever stage you
  are in. (The HARD keyword floor is wired but not yet populated — issue 07 — so
  for now also apply your own judgment on top of it as the SOFT layer.)

You never have to write to `session_state.json`; the hook does the per-turn tick.
You only flip the session on at the start and off at the end (below).

## Session lifecycle

State lives under the plugin's persistent data dir (`${CLAUDE_PLUGIN_DATA}`,
which resolves to `~/.claude/plugins/data/<plugin-id>/`), NOT in the plugin
install dir (that is wiped on update):

- `personas/<id>.json` — the persona to run (built by `/say-it-build`)
- `session_state.json` — the live session (managed for you by the hook)
- `takeaway_log.json` — append-only across-session log

**1. Start (S1 entry).** Once the user has picked a persona, activate the
session so the hook starts ticking:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py" --persona <id>
```

This writes an active `session_state.json` at stage `vent`, turn 0. Until this
runs, the hook stays silent — that is how it knows it is not in a say-it session.

**2. Entry revisit check (issue 03).** Before vent, match the user's opening
against prior issues for this persona to catch rumination. Matching is exact
string on `(persona_id, theme_label)` — `find_revisit` in `scripts/sayit_state.py`.
Same person + same theme = a revisit (ask a reflection question, don't block);
same person + different theme = a legitimately new issue (pass through).

**3. Run the stages.** Facilitate `vent` → `role-swap` → `integration` →
`closure`, reading `stage`/`turn`/guards from the injected reminder each turn.
The facilitation content is the later slices' job.

**4. Close (S4 bit 4 + 5).** When the takeaway is confirmed in the user's own
words, persist it, then end the session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_takeaway.py" \
  --persona <id> --theme "<label>" --takeaway "<user's own words, raw>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_end.py"
```

`session_end.py` flips `active` to false so the hook goes quiet. The session is
force-closed on one takeaway line — don't let it run on into between-session
rumination.

## Framing (always on)

This is not therapy or counseling — keep it a light "one round." The persona is
"the person as the user perceives them," not the real person. Don't send off the
*person* (they are alive; the user sees them tomorrow) — only put down *this one
knot*. See `references/SAFETY.md` for the full user-facing safety notice.

## State file shapes

Authoritative JSON Schemas: `references/schemas/persona.schema.json`,
`session_state.schema.json`, `takeaway_log.schema.json`. The deterministic
helpers that read/write them all live in `scripts/sayit_state.py`.
