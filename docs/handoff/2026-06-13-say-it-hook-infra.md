---
topic: say-it-hook-infra
date: 2026-06-13
---

# say-it — Hook infra + session state files (issue 01)

## Goal

Implement `docs/issues/01-hook-infra.md`: the deterministic execution foundation
for the say-it plugin — a `UserPromptSubmit` hook that ticks per-turn state (ADR
0004), three JSON state files (persona / session_state / takeaway_log), a draft
`/say-it` SKILL.md, a references bundle, and unit tests. This slice underpins all
later slices (issues 02–09).

## First Action

Nothing has executed yet — the scripts were written but never run. Smoke-test the
library before anything else to catch typos:

```bash
cd /Users/ljo/Desktop/project/zero-code/say-it
SAY_IT_DATA_DIR=/tmp/sayit-smoke python3 - <<'PY'
import sys; sys.path.insert(0, 'scripts')
import sayit_state as st
from pathlib import Path
dd = Path('/tmp/sayit-smoke')
st.start_session(dd, 'boss-kim')
s = st.load_session(dd)
st.tick(s, 'test message'); st.save_session(dd, s)
print('turn=', s['turn'], 'stage=', s['stage'])
print(st.render_reminder(s))
print('persona valid errors:', st.validate_persona(st.persona_template()))
PY
```

Expect: `turn= 1 stage= vent`, a rendered reminder block, and `persona valid
errors: []`. If that passes, proceed to Next Steps (write tests, then references).

## Context

Working through issue 01 task-by-task (TaskList #1–#8). Tasks 1–6 done (files
written, NOT yet run). Stopped on user request after finishing SKILL.md (task 6),
before references bundle (task 7) and unit tests (task 8). The whole slice is
untracked — nothing committed.

User constraints locked this session:
- **Conversation in Korean** (caveman ultra mode); **all implementation artifacts
  in English** (SKILL.md, schemas, scripts, comments, SAFETY). Exception: literal
  Korean bot-dialogue examples and the user's own vague labels stay Korean.
- Big slice → handing off mid-way by design.

## Current Progress

All new files are **untracked** (`git status`: `.claude-plugin/ hooks/
references scripts/ skills/`). Done so far:

| Path | What |
|---|---|
| `.claude-plugin/plugin.json` | manifest, name=say-it, v0.1.0 |
| `references/schemas/persona.schema.json` | 5 layers; L4.ambivalence **required**; provenance; corrections[] |
| `references/schemas/session_state.schema.json` | stage enum (vent/role-swap/integration/closure), turn, extension_used, `active` gate, guards (distress + turn_cap) |
| `references/schemas/takeaway_log.schema.json` | append-only entries: persona_id, theme_label, raw takeaway, at |
| `scripts/sayit_state.py` | **core lib**, zero-dep stdlib. load/save/new/start/end session, `tick`, `evaluate_guards`, `check_distress` (seam), `render_reminder`, `append_takeaway`, `find_revisit`, `validate_persona`, `persona_template`. Atomic writes. data_dir precedence: arg > `SAY_IT_DATA_DIR` > `CLAUDE_PLUGIN_DATA` |
| `scripts/tick.py` | hook entrypoint; gates on `active`, ticks, emits `hookSpecificOutput.additionalContext`; never exits 2 (won't erase prompt) |
| `scripts/session_start.py` `session_end.py` `save_takeaway.py` | model-invoked CLIs. All `chmod +x` |
| `hooks/hooks.json` | `UserPromptSubmit` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tick.py"`, timeout 10 |
| `skills/say-it/SKILL.md` | draft: system-reminder interpretation contract + session lifecycle (stage prompts deferred to issues 03/05/06) |

## Decisions Made

1. **Plugin root = repo root.** `docs/` co-resides; fine. Repo loads as a
   skills-dir plugin in place.
2. **PRD/ADR NOT bundled** into `references/` — judged over-specification in the
   issue's acceptance list (runtime never reads them; build reads them from
   `docs/` in-repo; bundling = duplication/drift). User approved. references/ =
   only `conflict-vocabulary.md` + `SAFETY.md`. ⚠️ This contradicts issue 01
   acceptance line "references/에 PRD, ADR 4개 ... 번들" — note as intentional.
3. **Spec corrections vs issue text** (issue used loose names): manifest =
   `.claude-plugin/plugin.json` (not `manifest.json`); persistent dir env =
   `${CLAUDE_PLUGIN_DATA}` → `~/.claude/plugins/data/<id>/` (not
   `$CLAUDE_PLUGIN_DATA_DIR`); plugin hooks live in `hooks/hooks.json` (NOT
   settings.json — plugin settings.json only supports `agent` /
   `subagentStatusLine`). Source: code.claude.com/docs plugins-reference + hooks.
4. **"Runs only when /say-it active"** = enforced in `tick.py` via the
   `session_state.active` gate, because `UserPromptSubmit` takes no matcher and
   fires globally. No active file → hook exits 0 silently.
5. **Distress = wired SEAM only** (`DISTRESS_PATTERNS = []`). Issue 07 fills the
   Korean keyword regexes + tier routing; call site (`check_distress`) is done.
6. **Turn-cap flags computed now** (soft@8/hard@11 booleans in guards), but
   enforcement copy is issue 04. Hook only *reports*; model acts.

## What Worked

- Verifying the plugin/hook spec against live docs (WebFetch on
  code.claude.com/docs/en/hooks + plugins-reference) before writing — caught all
  three naming mismatches in decision #3.
- Reading PRD + ADR 0003/0004 + CONTEXT.md first; the ambivalence-required and
  HARD-floor decisions came straight from there.

## Next Steps

1. **Smoke test** (First Action above).
2. **Task 8 — `tests/test_state.py`** (stdlib `unittest`, tmpdir-injected
   `SAY_IT_DATA_DIR`). Cover: start_session active/stage/turn0; tick increments
   0→1→2; turn-cap soft_hit at turn≥8, hard_hit at turn≥11; extension_used
   default False; end_session flips active; append_takeaway append-only (2 appends
   → 2 entries, first preserved); find_revisit exact match (same → hit, diff theme
   → miss, diff persona → miss); validate_persona pass on template, fail on
   missing L4.ambivalence and missing layer; distress seam wiring (inject a
   pattern into `DISTRESS_PATTERNS` → triggers; empty → clear). Run green.
   Acceptance: "상태 파일 읽기/쓰기/증분 유닛테스트". Consider `/tdd`.
3. **Task 7 — references bundle**: `references/conflict-vocabulary.md` (English
   prose/headers/tag-glosses, **preserve Korean label keys + Korean dialogue
   examples** — source: `docs/references/conflict-vocabulary.md`).
   `references/SAFETY.md` = **English stub** (issue 10 owns full content; just a
   placeholder + pointer so issue 01's scaffold list is satisfied).
4. **Manual hook-injection check** (acceptance: "Hook stdout → system-reminder
   주입 확인"): `/reload-plugins` or restart, run session_start, send a message,
   confirm the `[say-it session — authoritative state ...]` block appears in
   context and `session_state.json` turn incremented. May need the repo loaded as
   a plugin (`.claude/skills/` symlink or `--plugin-dir`).
5. **Commit** the slice once green.

## Acceptance Coverage (issue 01)

Covered by code (pending test verification): session_state create/update,
takeaway_log append-only, per-turn +1, persona schema (5 layers + corrections),
plugin scaffold + manifest, hook registration + skill-active gate. **Not yet
done**: unit tests (task 8), references bundle (task 7), live hook-injection
confirmation (step 4). SAFETY.md is a stub (full content = issue 10).

## Reference

- Issue: `docs/issues/01-hook-infra.md`
- Cross-slice contracts read this session: issues 02 (persona), 06 (closure/save),
  10 (safety); ADR 0003 (HARD safety gate), 0004 (state tick via hook); CONTEXT.md
  (ambivalence, issue/theme-label, hard-floor).
