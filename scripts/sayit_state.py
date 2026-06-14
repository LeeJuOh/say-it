#!/usr/bin/env python3
"""say-it state library: deterministic per-turn tick + state-file I/O.

This is the single source of truth for the three say-it state files. The hook
(tick.py) and the model-invoked CLIs (session_start.py, session_end.py,
save_takeaway.py) all go through here, so the on-disk shapes stay consistent and
the deterministic guard logic is unit-testable in one place.

Why standard library only: this code runs inside a UserPromptSubmit hook, which
fires on *every* user message and must start fast with whatever Python the user
already has. A third-party dependency (e.g. jsonschema) would be a fragile,
slow thing to import on the hot path, so validation here is hand-rolled.

Files under the data dir (see ``data_dir``):

    personas/<id>.json    persona build artifact   (shape only here; built in issue 02)
    session_state.json    within-session runtime    (stage, turn, extension, guards)
    takeaway_log.json     across-session log        (append-only; theme label + raw takeaway)

The authoritative schemas live in the skill bundle at
``skills/say-it/references/schemas/*.json``; the checks below mirror them.
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1

# The empty-chair arc. Order matters: S1 -> S2 -> S3 -> S4.
STAGES = ("vent", "role-swap", "integration", "closure")

# Anti-rumination turn budget. The hook only *flags* these; enforcement copy
# (when to invite the user onward, how the one-time extension works) is issue 04.
DEFAULT_SOFT_CAP = 8
DEFAULT_HARD_CAP = 11

# Distress detection SEAM. Issue 07 fills this with Korean-locale keyword regexes
# and tier routing. Empty here on purpose: issue 01 only wires the call site so
# the HARD floor (ADR 0003) has a deterministic home, it does not yet detect
# anything. Each entry is (compiled_or_raw_pattern, tier) where tier is
# "panic" or "acute-harm".
DISTRESS_PATTERNS: list[tuple[str, str]] = []


# --------------------------------------------------------------------------- #
# Paths and low-level JSON I/O
# --------------------------------------------------------------------------- #

def _now() -> str:
    """UTC ISO-8601 to the second. Real subprocess, so wall-clock is fine here."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def data_dir(explicit: str | os.PathLike | None = None) -> Path | None:
    """Resolve the persistent data directory.

    Precedence: explicit arg > SAY_IT_DATA_DIR (dev/test override) >
    CLAUDE_PLUGIN_DATA (production, exported by Claude Code into hook processes).

    Returns None when nothing is set, so callers on the hot path can bail out
    quietly instead of guessing a location and writing state somewhere wrong.
    """
    resolved = (
        explicit
        or os.environ.get("SAY_IT_DATA_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
    )
    return Path(resolved) if resolved else None


def _session_path(dd: Path) -> Path:
    return Path(dd) / "session_state.json"


def _log_path(dd: Path) -> Path:
    return Path(dd) / "takeaway_log.json"


def _persona_path(dd: Path, persona_id: str) -> Path:
    return Path(dd) / "personas" / f"{persona_id}.json"


def _read_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json_atomic(path: Path, obj) -> None:
    """Write via a temp file + os.replace so a crashed/concurrent write can never
    leave a half-written state file. The hook runs on every turn; a torn write
    here would corrupt the session, so the atomic swap is worth the few lines."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------- #
# session_state
# --------------------------------------------------------------------------- #

def new_session(persona_id: str | None = None,
                session_id: str | None = None,
                soft_cap: int = DEFAULT_SOFT_CAP,
                hard_cap: int = DEFAULT_HARD_CAP) -> dict:
    """Build a fresh, active session_state dict at stage S1 (vent), turn 0."""
    now = _now()
    return {
        "schema_version": SCHEMA_VERSION,
        "active": True,
        "session_id": session_id,
        "persona_id": persona_id,
        "theme_label": None,
        "stage": "vent",
        "turn": 0,
        "extension_used": False,
        "started_at": now,
        "updated_at": now,
        "guards": {
            "distress": {"triggered": False, "tier": None},
            "turn_cap": {
                "soft": soft_cap,
                "hard": hard_cap,
                "soft_hit": False,
                "hard_hit": False,
            },
        },
    }


def load_session(dd: Path) -> dict | None:
    """Return the current session_state dict, or None if there is no session file."""
    return _read_json(_session_path(dd), None)


def save_session(dd: Path, state: dict) -> None:
    state["updated_at"] = _now()
    _write_json_atomic(_session_path(dd), state)


def start_session(dd: Path, persona_id: str | None = None,
                  session_id: str | None = None,
                  theme_label: str | None = None) -> dict:
    """Activate a new session and persist it. Called by /say-it at S1 entry.

    This (not the hook) is what creates the active state, which is exactly how
    the globally-firing hook stays silent outside a say-it session: no active
    file, no tick."""
    state = new_session(persona_id=persona_id, session_id=session_id)
    state["theme_label"] = theme_label
    save_session(dd, state)
    return state


def end_session(dd: Path) -> dict | None:
    """Deactivate the session (closure / safety stop). The file is kept so the
    last state is inspectable; only the gate flag flips."""
    state = load_session(dd)
    if state is None:
        return None
    state["active"] = False
    save_session(dd, state)
    return state


def check_distress(prompt: str) -> dict:
    """HARD-floor distress check (ADR 0003). Scans DISTRESS_PATTERNS, which issue
    01 leaves empty: the seam is wired so issue 07 only has to supply the Korean
    keyword regexes and never touch the call site. Returns the highest-severity
    match (acute-harm outranks panic)."""
    import re

    hit_tier = None
    for pattern, tier in DISTRESS_PATTERNS:
        if re.search(pattern, prompt):
            if tier == "acute-harm":
                return {"triggered": True, "tier": "acute-harm"}
            hit_tier = hit_tier or tier
    if hit_tier:
        return {"triggered": True, "tier": hit_tier}
    return {"triggered": False, "tier": None}


def evaluate_guards(state: dict, prompt: str) -> dict:
    """Recompute the per-turn guard block from the current turn count and prompt.
    Pure function of (state, prompt): returns a fresh guards dict, mutates nothing."""
    cap = state.get("guards", {}).get("turn_cap", {})
    soft = cap.get("soft", DEFAULT_SOFT_CAP)
    hard = cap.get("hard", DEFAULT_HARD_CAP)
    turn = state.get("turn", 0)
    return {
        "distress": check_distress(prompt),
        "turn_cap": {
            "soft": soft,
            "hard": hard,
            "soft_hit": turn >= soft,
            "hard_hit": turn >= hard,
        },
    }


def tick(state: dict, prompt: str = "") -> dict:
    """The per-turn tick (ADR 0004): +1 the turn counter, then recompute guards
    against the new count and this turn's prompt. Mutates and returns `state`."""
    state["turn"] = state.get("turn", 0) + 1
    state["guards"] = evaluate_guards(state, prompt)
    state["updated_at"] = _now()
    return state


def render_reminder(state: dict) -> str:
    """Render the authoritative system-reminder the hook injects each turn.

    This is the hook->model contract: the model reads stage / turn / cap / distress
    from THIS, refreshed every turn, rather than re-deriving them from a long
    conversation it might mis-count (the context-rot failure ADR 0004 guards
    against). English by design — runtime instructions to the model, not user copy."""
    g = state.get("guards", {})
    cap = g.get("turn_cap", {})
    distress = g.get("distress", {})
    soft, hard = cap.get("soft"), cap.get("hard")
    turn = state.get("turn", 0)

    if cap.get("hard_hit"):
        cap_line = f"turn-cap: {turn}/{soft} soft, HARD CEILING {hard} REACHED"
    elif cap.get("soft_hit"):
        cap_line = f"turn-cap: SOFT CAP {soft} REACHED (turn {turn}, hard ceiling {hard})"
    else:
        cap_line = f"turn-cap: turn {turn} (soft {soft}, hard {hard}) — not reached"

    if distress.get("triggered"):
        distress_line = f"distress guard: TRIGGERED tier={distress.get('tier')}"
    else:
        distress_line = "distress guard: clear"

    lines = [
        "[say-it session — authoritative state, refreshed this turn by the hook]",
        f"persona: {state.get('persona_id')} | stage: {state.get('stage')} | turn: {turn}",
        f"theme: {state.get('theme_label')} | extension used: {state.get('extension_used')}",
        cap_line,
        distress_line,
        "This block is machine-owned and overrides any stage or count you infer "
        "from the conversation. Honor `stage` and the cap policy. If the distress "
        "guard is TRIGGERED, stop the session and follow the safety path "
        "(panic -> de-escalate; acute-harm -> crisis hotline, no resume) "
        "regardless of stage.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# takeaway_log  (append-only)
# --------------------------------------------------------------------------- #

def _empty_log() -> dict:
    return {"schema_version": SCHEMA_VERSION, "entries": []}


def load_log(dd: Path) -> dict:
    log = _read_json(_log_path(dd), None)
    if not isinstance(log, dict) or "entries" not in log:
        return _empty_log()
    return log


def append_takeaway(dd: Path, persona_id: str, theme_label: str,
                    takeaway: str, session_id: str | None = None) -> dict:
    """Append one entry to the takeaway log. Append-only: existing entries are
    never read-modified-rewritten, only added to. Takeaway is stored RAW."""
    log = load_log(dd)
    log["entries"].append({
        "persona_id": persona_id,
        "theme_label": theme_label,
        "takeaway": takeaway,
        "session_id": session_id,
        "at": _now(),
    })
    _write_json_atomic(_log_path(dd), log)
    return log


def find_revisit(dd: Path, persona_id: str, theme_label: str) -> list[dict]:
    """Exact-string match on (persona_id, theme_label) = the 'issue'. Returns prior
    entries for the same issue (revisit guard, issue 03). Same person + different
    theme = different issue = no match = legitimate revisit, not exiled."""
    return [
        e for e in load_log(dd).get("entries", [])
        if e.get("persona_id") == persona_id and e.get("theme_label") == theme_label
    ]


# --------------------------------------------------------------------------- #
# persona validation  (shape defined here; built in issue 02)
# --------------------------------------------------------------------------- #

_PERSONA_LAYERS = (
    "L0_hard_rules",
    "L1_identity",
    "L2_voice",
    "L3_emotional_triggers",
    "L4_relationship_dynamics",
)


def validate_persona(obj) -> list[str]:
    """Lightweight structural check mirroring persona.schema.json. Returns a list
    of error strings (empty list = valid). Not a full JSON-Schema validator — just
    the invariants issue 02 must not violate, checkable with zero dependencies."""
    errors: list[str] = []
    if not isinstance(obj, dict):
        return ["persona must be a JSON object"]

    if obj.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(obj.get("id"), str) or not obj.get("id"):
        errors.append("id must be a non-empty string")
    if not isinstance(obj.get("corrections"), list):
        errors.append("corrections must be an array (may be empty)")

    layers = obj.get("layers")
    if not isinstance(layers, dict):
        errors.append("layers must be an object with L0..L4")
        return errors

    for layer in _PERSONA_LAYERS:
        if layer not in layers:
            errors.append(f"missing layer {layer}")

    # L4's ambivalence field is required: the person's own contradiction is the
    # rumination engine, so it is a core field, not optional decoration.
    l4 = layers.get("L4_relationship_dynamics")
    if isinstance(l4, dict):
        if not isinstance(l4.get("ambivalence"), str) or not l4.get("ambivalence"):
            errors.append("L4_relationship_dynamics.ambivalence is required (preserve the person's contradiction)")
    elif "L4_relationship_dynamics" in layers:
        errors.append("L4_relationship_dynamics must be an object")

    l0 = layers.get("L0_hard_rules")
    if "L0_hard_rules" in layers and (not isinstance(l0, list) or not l0):
        errors.append("L0_hard_rules must be a non-empty array")

    return errors


def save_persona(dd: Path, persona: dict) -> Path:
    """Validate then atomically write a persona to ``personas/<id>.json``.

    This is the single on-disk write path for the build skill (issue 02): the
    skill constructs the persona dict, this is the only thing that puts it on
    disk, so ``validate_persona`` runs exactly once at the boundary and a
    structurally-broken persona can never reach the session runner. Raises
    ``ValueError`` carrying the structural errors so the caller (the
    save_persona CLI) can surface them and the model can fix and retry rather
    than silently shipping a bad file.
    """
    errors = validate_persona(persona)
    if errors:
        raise ValueError("invalid persona: " + "; ".join(errors))
    path = _persona_path(dd, persona["id"])
    _write_json_atomic(path, persona)
    return path


def load_persona(dd: Path, persona_id: str) -> dict | None:
    """Return the persona dict for ``persona_id``, or None if there is no file.
    The session runner (issue 03) reads the persona to drive the session; the
    build skill uses it to show a just-saved persona back to the user."""
    return _read_json(_persona_path(dd, persona_id), None)


def list_personas(dd: Path) -> list[str]:
    """List existing persona ids (filename stems) under ``personas/``, sorted.

    Multi-persona lives as multiple files in one directory, so this is how the
    build skill spots an id collision before overwriting and how the runner
    offers the user a choice of who to sit across from. Empty list when the
    directory does not exist yet."""
    pdir = Path(dd) / "personas"
    if not pdir.is_dir():
        return []
    return sorted(p.stem for p in pdir.glob("*.json"))


def persona_template(persona_id: str = "boss-kim") -> dict:
    """A minimal valid persona, for tests and as a concrete reference for issue 02.

    Values are English placeholders that describe the SHAPE only. In production
    the layers are filled with the user's own narration in their own language —
    that runtime text is data, not part of this code. Keeping the fixture in
    English follows the rule that plugin source stays English; the bot's
    language-specific voice comes from L2 at build time, not from here."""
    return {
        "schema_version": SCHEMA_VERSION,
        "id": persona_id,
        "display_name": "Team Lead Kim",
        "relationship": "workplace boss",
        "layers": {
            "L0_hard_rules": [
                "no escalation to verbal abuse",
                "no attacking the user",
                "no suddenly-nice fake apology or comfort",
            ],
            "L1_identity": {
                "who": "team lead, 7 years senior",
                "role": "workplace boss",
                "relation_to_user": "same team",
            },
            "L2_voice": {
                "tone": "informal, clipped",
                "verbal_tics": ["so anyway~", "so?"],
                "calls_user": "by first name",
            },
            "L3_emotional_triggers": [
                {"trigger": "having a mistake pointed out", "reaction": "snaps back defensively"},
            ],
            "L4_relationship_dynamics": {
                "conflict_pattern": "dismisses in meetings -> bad-mouths behind back -> user endures it",
                "typical_fight": "credit-stealing",
                "what_user_wants": "recognition, not an apology",
                "ambivalence": "usually cold and dismissive, then occasionally looks out for the user out of nowhere",
            },
        },
        "provenance": {
            "L1_identity": "narrated",
            "L3_emotional_triggers": "inferred",
        },
        "corrections": [],
    }
