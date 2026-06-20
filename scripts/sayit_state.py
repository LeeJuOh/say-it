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

# Distress detection (ADR 0003 HARD floor). The Korean-locale keyword regexes and
# the crisis-hotline resource are runtime *data*, not source prose, so they live in
# a JSON lexicon OUTSIDE the English-source tree -- scripts/skills/tests stay
# Hangul-free so the gate `grep -rlP '[\x{AC00}-\x{D7A3}]' scripts skills tests` is 0.
# The lexicon is loaded once at import (see the bottom of this file) into
# DISTRESS_PATTERNS and DISTRESS_HOTLINE. Each pattern entry is (raw_regex, tier),
# tier being "panic" (Grade 1) or "acute-harm" (Grade 2); check_distress scans them
# every turn.
#
# The discriminator the regexes encode is DIRECTION, not intensity: rage aimed at
# the OTHER person is normal catharsis for this product and must never fire, while
# the user's OWN self-directed distress must. That self/other split is the whole
# safety design -- see the per-pattern notes in lexicon/distress.ko.json and the
# labelled corpus in lexicon/distress_examples.ko.json that the tests assert against.
# Defaults here are placeholders; the real values land at the module-bottom load.
DISTRESS_PATTERNS: list[tuple[str, str]] = []
DISTRESS_HOTLINE: dict | None = None


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


def _lexicon_dir() -> Path:
    """The runtime data lexicon ships alongside scripts/ at the plugin root, one
    level up from this file. It is kept out of scripts/skills/tests so its Korean
    keyword data never trips the English-source gate."""
    return Path(__file__).resolve().parent.parent / "lexicon"


def load_distress_lexicon(path: Path | None = None):
    """Load the distress keyword patterns + crisis-hotline resource from the JSON
    lexicon. Returns ``(patterns, hotline)`` where patterns is a list of
    ``(raw_regex, tier)``.

    A missing or malformed lexicon degrades to ``([], None)`` rather than raising:
    this is read on the hook's hot path, which must never crash, and the SOFT model
    layer still stands if the floor goes dark. That degradation is a runtime
    backstop, not the expected path -- the test suite asserts the shipped lexicon
    actually loads, so an empty floor in production means a broken install, not a
    silent design choice."""
    data = _read_json(path or (_lexicon_dir() / "distress.ko.json"), {})
    patterns: list[tuple[str, str]] = []
    for entry in data.get("patterns", []):
        pat, tier = entry.get("pattern"), entry.get("tier")
        if pat and tier in ("panic", "acute-harm"):
            patterns.append((pat, tier))
    return patterns, data.get("hotline")


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
        # Terminal safety latch (ADR 0003). Set True only by the distress
        # circuit-breaker on an acute-harm (Grade 2) signal; once True the session
        # will not resume (the hook re-injects a hold, start_session refuses).
        # Distinct from the persona-level block (issue 08).
        "blocked": False,
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
    file, no tick.

    Refuses to start over a BLOCKED session: an acute-harm (Grade 2) stop is
    terminal (ADR 0003 "no resume"), so a new round is not silently opened on top
    of it. The refusal is the resume-gate at the *entry*, paired with the hook's
    per-turn hold re-injection. Raises ValueError so the session_start CLI can
    surface the hold + crisis hotline instead of writing a fresh active session."""
    existing = load_session(dd)
    if existing and existing.get("blocked"):
        raise ValueError(
            "session is on a safety hold (acute-distress block) and will not "
            "resume; surface the crisis hotline rather than starting a new round")
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


def block_session(dd: Path) -> dict | None:
    """Latch the on-disk session BLOCKED (terminal safety hold) and deactivate it.

    The HARD floor already latches this in-memory inside ``tick`` when its regexes
    catch an acute-harm signal. This is the *disk-level* path, exposed via
    session_block.py, so the SOFT model layer can latch the same hold when it
    catches an acute-harm signal the keyword floor missed (an oblique phrasing,
    somatic crisis). Both detection layers therefore converge on the same
    resume-refusal, instead of SOFT-detected harm quietly leaving the session
    resumable. Returns None when there is no session to block."""
    state = load_session(dd)
    if state is None:
        return None
    state["blocked"] = True
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
    Pure function of (state, prompt): returns a fresh guards dict, mutates nothing.

    The turn cap is **vent-only** (issue 04 / ADR rationale): vent is the open
    pour-it-out stage where rumination can run away, so it is the one stage with a
    budget. role-swap / integration / closure are already structured and bounded by
    their own facilitation, so the cap would only get in their way — hence the
    `in_vent` gate that holds soft_hit/hard_hit False outside vent no matter how
    high `turn` has climbed (the counter stays monotonic across stages; only its
    *meaning* is vent-scoped)."""
    cap = state.get("guards", {}).get("turn_cap", {})
    soft = cap.get("soft", DEFAULT_SOFT_CAP)
    hard = cap.get("hard", DEFAULT_HARD_CAP)
    turn = state.get("turn", 0)
    in_vent = state.get("stage") == "vent"
    return {
        "distress": check_distress(prompt),
        "turn_cap": {
            "soft": soft,
            "hard": hard,
            "soft_hit": in_vent and turn >= soft,
            "hard_hit": in_vent and turn >= hard,
        },
    }


def advance_stage(dd: Path, next_stage: str) -> dict:
    """Forward-only stage transition (issue 04). Loads the active session, verifies
    that ``next_stage`` is the *immediate* successor of the current stage, writes
    it, and returns the updated state.

    Forward-only is the whole point: the empty-chair arc only moves one direction
    (vent -> role-swap -> integration -> closure). Going back to a finished stage or
    skipping one would desync the hook's stage-gated logic (e.g. re-entering vent
    would re-arm the turn cap) and break the ritual's shape. So this rejects
    backward moves, skips, unknown names, and advancing past closure — raising
    ``ValueError`` with a message the thin CLI surfaces, so the model can read why
    and retry rather than silently landing in a wrong stage."""
    if next_stage not in STAGES:
        raise ValueError(
            f"unknown stage {next_stage!r}; must be one of {', '.join(STAGES)}")
    state = load_session(dd)
    if state is None:
        raise ValueError("no active session to advance (session_state.json absent)")
    current = state.get("stage")
    try:
        cur_i = STAGES.index(current)
    except ValueError:
        raise ValueError(f"current stage {current!r} is not a known stage")
    expected = STAGES[cur_i + 1] if cur_i + 1 < len(STAGES) else None
    if next_stage != expected:
        if expected is None:
            raise ValueError(
                f"already at the final stage {current!r}; nothing to advance to")
        raise ValueError(
            f"forward-only: from {current!r} the only valid next stage is "
            f"{expected!r}, not {next_stage!r}")
    state["stage"] = next_stage
    save_session(dd, state)
    return state


def use_extension(dd: Path) -> dict:
    """Spend the one-time vent extension — the user's "give me a bit more room"
    past the soft cap (issue 04). Loads the active session, flips the
    ``extension_used`` latch, persists, returns the updated state.

    The latch is what makes "exactly once per session" enforceable in *code* rather
    than relying on the model to remember: a second call raises, so the +3 room
    between the soft cap (8) and the hard ceiling (11) can be granted at most once.
    Vent-only, because that is the only stage the cap applies to — calling it
    elsewhere is a logic error worth surfacing, not a silent no-op."""
    state = load_session(dd)
    if state is None:
        raise ValueError("no active session to extend (session_state.json absent)")
    if state.get("stage") != "vent":
        raise ValueError(
            f"the extension only applies in vent (current stage is {state.get('stage')!r})")
    if state.get("extension_used"):
        raise ValueError("extension already used (one per session)")
    state["extension_used"] = True
    save_session(dd, state)
    return state


def tick(state: dict, prompt: str = "") -> dict:
    """The per-turn tick (ADR 0004): +1 the turn counter, then recompute guards
    against the new count and this turn's prompt. Mutates and returns `state`."""
    state["turn"] = state.get("turn", 0) + 1
    state["guards"] = evaluate_guards(state, prompt)
    # Acute-harm (Grade 2) is terminal and unbypassable: latch the session BLOCKED
    # and inactive right here in code, so resume-refusal never depends on the model
    # choosing to stop (the model-goodwill failure ADR 0003 forbids). Panic (Grade 1)
    # is render-only -- the model de-escalates and winds down -- so it does NOT latch.
    if state["guards"].get("distress", {}).get("tier") == "acute-harm":
        state["blocked"] = True
        state["active"] = False
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
    extension_used = state.get("extension_used", False)

    # cap_marker is the machine-readable token the model branches on; cap_line is
    # the human-readable status. Both are already vent-only because soft_hit /
    # hard_hit are gated on stage in evaluate_guards — outside vent they are False,
    # so this lands in the "not reached" branch and emits no marker. The SOFT
    # marker is suppressed once the extension is spent: the user already chose
    # "more room," so re-firing the invite every turn would nag, exactly the
    # re-suppression the cap copy is written to avoid (invitation, not exile). HARD
    # still fires through a spent extension — the ceiling is non-negotiable.
    cap_marker = None
    if cap.get("hard_hit"):
        cap_line = f"turn-cap: {turn}/{soft} soft, HARD CEILING {hard} REACHED"
        cap_marker = "CAP_TRIGGERED: HARD"
    elif cap.get("soft_hit") and not extension_used:
        cap_line = f"turn-cap: SOFT CAP {soft} REACHED (turn {turn}, hard ceiling {hard})"
        cap_marker = "CAP_TRIGGERED: SOFT"
    elif cap.get("soft_hit"):  # soft passed but extension already spent
        cap_line = (f"turn-cap: soft {soft} passed, extension spent, "
                    f"running to hard ceiling {hard} (turn {turn})")
    else:
        cap_line = f"turn-cap: turn {turn} (soft {soft}, hard {hard}) — not reached"

    # Distress lines carry a machine-readable GRADE marker the model branches on,
    # the same way the cap emits CAP_TRIGGERED. GRADE_2 (acute-harm) also prints the
    # crisis hotline verbatim so the model relays a *fact the hook injected*, not a
    # number it recalled, and announces the code-level BLOCKED latch.
    distress_lines: list[str] = []
    if distress.get("triggered"):
        tier = distress.get("tier")
        distress_lines.append(f"distress guard: TRIGGERED tier={tier}")
        if tier == "acute-harm":
            distress_lines.append("DISTRESS_TRIGGERED: GRADE_2")
            distress_lines.append(_hotline_line())
            distress_lines.append(
                "session BLOCKED: acute self-harm signal — this session will not "
                "resume. Break character now, surface the crisis hotline above "
                "verbatim, and do not continue the empty-chair exercise.")
        else:  # panic
            distress_lines.append("DISTRESS_TRIGGERED: GRADE_1")
            distress_lines.append(
                "Break character now; de-escalate gently and wind the session down. "
                "This is not a normal closure (no takeaway ritual) — a soft landing.")
    else:
        distress_lines.append("distress guard: clear")

    lines = [
        "[say-it session — authoritative state, refreshed this turn by the hook]",
        f"persona: {state.get('persona_id')} | stage: {state.get('stage')} | turn: {turn}",
        f"theme: {state.get('theme_label')} | extension used: {extension_used}",
        cap_line,
    ]
    if cap_marker:
        lines.append(cap_marker)
    lines += distress_lines
    lines.append(
        "This block is machine-owned and overrides any stage or count you infer "
        "from the conversation. Honor `stage` and the cap policy. If the distress "
        "guard is TRIGGERED, stop the session immediately and follow the safety path "
        "(GRADE_1 panic -> de-escalate and wind down; GRADE_2 acute-harm -> surface "
        "the crisis hotline, no resume) regardless of stage or turn count.")
    return "\n".join(lines)


def hotline_text() -> str:
    """Render the crisis-hotline resource as the single user-facing string
    ("name number (hours)"). This is the one place the lexicon's hotline becomes
    human-facing text, so every surface that shows it -- the runtime reminder, the
    start-up safety refusal, and the build-entry notice -- reads the same value and
    can never drift (issue 10, no-mismatch rule). Empty string if the lexicon is absent;
    callers decide the fallback wording for their context."""
    h = DISTRESS_HOTLINE
    if not h:
        return ""
    label = " ".join(p for p in (h.get("name"), h.get("number")) if p)
    if h.get("hours"):
        label += f" ({h['hours']})"
    return label


def _hotline_line() -> str:
    """The runtime-reminder form: the user-facing hotline string prefixed for the
    model to relay verbatim. Degrades to a generic pointer if the lexicon is absent,
    so the model still surfaces *something* rather than a blank."""
    label = hotline_text()
    if not label:
        return "crisis hotline: (resource unavailable — surface a local crisis line)"
    return f"crisis hotline: {label}"


def render_safety_hold(state: dict) -> str:
    """Re-injected every turn while a session carries the BLOCKED latch (from a prior
    acute-harm trigger). It re-asserts the hold so the conversation cannot drift back
    into the empty-chair session after a Grade-2 stop — the resume-refusal seen from
    *inside* the same conversation, complementing start_session's refusal of a *new*
    session. Kept minimal: the hold and the hotline, nothing that invites continuing."""
    lines = [
        "[say-it session — SAFETY HOLD, machine-owned]",
        "This session was stopped on an acute self-harm signal and is on a safety "
        "hold; it will not resume. Do not continue the empty-chair exercise or "
        "re-enter the persona.",
        _hotline_line(),
        "Stay with the user plainly and keep the crisis hotline above in front of them.",
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
    persona_id = obj.get("id")
    if not isinstance(persona_id, str) or not persona_id:
        errors.append("id must be a non-empty string")
    else:
        # id becomes a file path component (_persona_path -> personas/<id>.json),
        # so enforce the slug pattern from persona.schema.json here at the write
        # boundary. Without it a model-generated id like "../x" would escape the
        # personas dir (path traversal). Mirrors schema pattern
        # ^[a-z0-9]+(?:-[a-z0-9]+)*$ (M1).
        import re
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", persona_id):
            errors.append("id must be a slug: lowercase a-z, 0-9, hyphen-separated "
                          "(e.g. 'boss-jane'); no slashes, dots, or path segments")
    corrections = obj.get("corrections")
    if not isinstance(corrections, list):
        errors.append("corrections must be an array (may be empty)")
    else:
        # corrections is the single write path for issue 08; check each item's
        # shape here, at the same boundary save_persona guards, so a malformed
        # correction can never land on disk. Mirrors persona.schema.json's
        # items.required: ["at", "layer", "note"].
        for i, c in enumerate(corrections):
            if not isinstance(c, dict):
                errors.append(f"corrections[{i}] must be an object")
                continue
            if c.get("layer") not in _PERSONA_LAYERS:
                errors.append(f"corrections[{i}].layer must be one of L0..L4")
            if not isinstance(c.get("note"), str) or not c.get("note"):
                errors.append(f"corrections[{i}].note is required (what the user says is wrong)")
            if not isinstance(c.get("at"), str) or not c.get("at"):
                errors.append(f"corrections[{i}].at timestamp is required")

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


def append_correction(dd: Path, persona_id: str, layer: str, note: str,
                      before: str | None = None, after: str | None = None) -> dict:
    """Append one user correction to a persona and persist it (issue 08).

    The trigger is the user saying "the real person isn't like that" during or
    after a session. Layering is *non-destructive*: the built L0..L4 layers are
    never read-modified-rewritten here — only the append-only ``corrections``
    array grows, each entry carrying its own trace (``at``/``layer``/``note`` plus
    optional before->after) so the drift from the built persona toward the user's
    perception stays auditable. The note is the user's runtime data, stored RAW.

    The write goes through ``save_persona`` so the same boundary validation that
    guards the build rejects a malformed correction (bad layer, empty note) before
    it lands. Raises ``ValueError`` if ``persona_id`` has no file to correct.
    """
    persona = load_persona(dd, persona_id)
    if persona is None:
        raise ValueError(f"no persona {persona_id!r} to correct")
    entry = {"at": _now(), "layer": layer, "note": note}
    if before is not None:
        entry["from"] = before
    if after is not None:
        entry["to"] = after
    persona.setdefault("corrections", []).append(entry)
    save_persona(dd, persona)
    return persona


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


# --------------------------------------------------------------------------- #
# Distress lexicon load (runs once at import)
# --------------------------------------------------------------------------- #

# Done here, at the bottom, so the call can use the helpers defined above
# (_read_json / _lexicon_dir). check_distress / render_reminder resolve these
# module globals at call time, so the load just has to finish before the first
# turn — which it does, at import. Tests that exercise the empty seam reassign
# DISTRESS_PATTERNS directly and restore it, so they stay independent of this.
DISTRESS_PATTERNS, DISTRESS_HOTLINE = load_distress_lexicon()
