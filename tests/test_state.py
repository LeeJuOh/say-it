#!/usr/bin/env python3
"""Unit tests for sayit_state — the deterministic core of the say-it plugin.

These lock down the invariants the rest of the slices depend on: the per-turn
tick (ADR 0004), the turn-cap and distress guards (ADR 0003), the append-only
takeaway log, the exact-match revisit lookup, and the persona shape. Standard
library only (``unittest``), so they run with whatever Python the hook uses.

Each test gets its own tmp data dir, so there is no shared on-disk state and the
suite is order-independent. Run from the repo root::

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# scripts/ is a sibling of tests/, not an installed package, so put it on the
# path the same way the hook does for its own imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayit_state as st  # noqa: E402


class StateTestCase(unittest.TestCase):
    """Base case giving each test an isolated tmp data dir at ``self.dd``."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dd = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestSessionLifecycle(StateTestCase):
    def test_start_session_initial_state(self):
        state = st.start_session(self.dd, persona_id="boss-kim",
                                 theme_label="boss/credit-theft")
        self.assertTrue(state["active"])
        self.assertEqual(state["stage"], "vent")          # always enters at S1
        self.assertEqual(state["turn"], 0)                # tick happens on the hook, not here
        self.assertFalse(state["extension_used"])         # one-time extension unused at start
        self.assertEqual(state["persona_id"], "boss-kim")
        self.assertEqual(state["theme_label"], "boss/credit-theft")

    def test_start_session_persists_and_reloads(self):
        st.start_session(self.dd, persona_id="boss-kim")
        reloaded = st.load_session(self.dd)
        self.assertIsNotNone(reloaded)
        self.assertTrue(reloaded["active"])
        self.assertEqual(reloaded["persona_id"], "boss-kim")

    def test_load_session_none_when_absent(self):
        # No session file yet -> the globally-firing hook must see "no session".
        self.assertIsNone(st.load_session(self.dd))

    def test_end_session_flips_active_but_keeps_file(self):
        st.start_session(self.dd, persona_id="boss-kim")
        ended = st.end_session(self.dd)
        self.assertFalse(ended["active"])
        # File is kept (last state inspectable); only the gate flag flipped.
        self.assertFalse(st.load_session(self.dd)["active"])

    def test_end_session_none_when_no_session(self):
        self.assertIsNone(st.end_session(self.dd))


class TestTick(StateTestCase):
    def test_tick_increments_turn(self):
        state = st.new_session(persona_id="boss-kim")
        self.assertEqual(state["turn"], 0)
        st.tick(state, "first message")
        self.assertEqual(state["turn"], 1)
        st.tick(state, "second message")
        self.assertEqual(state["turn"], 2)

    def test_tick_recomputes_guards_each_turn(self):
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, "msg")
        self.assertIn("distress", state["guards"])
        self.assertIn("turn_cap", state["guards"])
        self.assertEqual(state["guards"]["turn_cap"]["soft_hit"], False)


class TestTurnCapGuard(StateTestCase):
    """Anti-rumination budget: soft at 8, hard at 11. The hook only flags; the
    enforcement copy is issue 04. Here we only assert the booleans flip on the
    right turn so issue 04 can trust them."""

    def test_soft_hit_at_or_after_soft_cap(self):
        state = st.new_session()
        state["turn"] = 7
        self.assertFalse(st.evaluate_guards(state, "")["turn_cap"]["soft_hit"])
        state["turn"] = 8
        guards = st.evaluate_guards(state, "")
        self.assertTrue(guards["turn_cap"]["soft_hit"])
        self.assertFalse(guards["turn_cap"]["hard_hit"])

    def test_hard_hit_at_or_after_hard_cap(self):
        state = st.new_session()
        state["turn"] = 10
        self.assertFalse(st.evaluate_guards(state, "")["turn_cap"]["hard_hit"])
        state["turn"] = 11
        guards = st.evaluate_guards(state, "")
        self.assertTrue(guards["turn_cap"]["hard_hit"])
        self.assertTrue(guards["turn_cap"]["soft_hit"])  # hard implies soft

    def test_evaluate_guards_is_pure(self):
        # Returns a fresh dict, mutates nothing — issue 04 may call it speculatively.
        state = st.new_session()
        state["turn"] = 5
        before = state["guards"]
        st.evaluate_guards(state, "msg")
        self.assertIs(state["guards"], before)


class TestDistressSeam(StateTestCase):
    """ADR 0003 HARD floor. Issue 01 wires the call site only; DISTRESS_PATTERNS
    is empty. We patch a pattern in to prove the seam routes, then confirm the
    empty default stays clear — so issue 07 can fill regexes without touching
    the call site."""

    def tearDown(self):
        st.DISTRESS_PATTERNS = []  # restore the empty seam for other tests
        super().tearDown()

    def test_empty_patterns_never_trigger(self):
        st.DISTRESS_PATTERNS = []
        result = st.check_distress("anything at all")
        self.assertFalse(result["triggered"])
        self.assertIsNone(result["tier"])

    def test_injected_pattern_triggers_with_tier(self):
        # The pattern is arbitrary here — issue 01 tests the wiring, not real
        # keywords (those are issue 07, and locale-specific).
        st.DISTRESS_PATTERNS = [("panicking", "panic")]
        result = st.check_distress("i am panicking right now")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["tier"], "panic")

    def test_acute_harm_outranks_panic(self):
        # Order independent: acute-harm must win even when listed after panic.
        st.DISTRESS_PATTERNS = [("anxious", "panic"), ("hurt myself", "acute-harm")]
        result = st.check_distress("i'm anxious and want to hurt myself")
        self.assertEqual(result["tier"], "acute-harm")

    def test_tick_surfaces_distress_into_guards(self):
        st.DISTRESS_PATTERNS = [("hurt myself", "acute-harm")]
        state = st.new_session()
        st.tick(state, "i want to hurt myself")
        self.assertTrue(state["guards"]["distress"]["triggered"])
        self.assertEqual(state["guards"]["distress"]["tier"], "acute-harm")


class TestTakeawayLog(StateTestCase):
    """The log is append-only: closing a session adds an entry, never rewrites
    history. The revisit guard reads it by exact (persona, theme) = 'issue'."""

    def test_append_only_preserves_prior_entries(self):
        st.append_takeaway(self.dd, "boss-kim", "boss/credit-theft", "first takeaway")
        st.append_takeaway(self.dd, "boss-kim", "boss/credit-theft", "second takeaway")
        entries = st.load_log(self.dd)["entries"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["takeaway"], "first takeaway")  # first untouched
        self.assertEqual(entries[1]["takeaway"], "second takeaway")

    def test_empty_log_when_absent(self):
        self.assertEqual(st.load_log(self.dd)["entries"], [])

    def test_find_revisit_exact_match_hits(self):
        st.append_takeaway(self.dd, "boss-kim", "boss/credit-theft", "t")
        hits = st.find_revisit(self.dd, "boss-kim", "boss/credit-theft")
        self.assertEqual(len(hits), 1)

    def test_find_revisit_different_theme_misses(self):
        # Same person, different grievance theme = a *different* issue = legit
        # revisit, not exiled.
        st.append_takeaway(self.dd, "boss-kim", "boss/credit-theft", "t")
        self.assertEqual(st.find_revisit(self.dd, "boss-kim", "boss/micromanaging"), [])

    def test_find_revisit_different_persona_misses(self):
        st.append_takeaway(self.dd, "boss-kim", "boss/credit-theft", "t")
        self.assertEqual(st.find_revisit(self.dd, "mom", "boss/credit-theft"), [])


class TestPersonaValidation(StateTestCase):
    def test_template_is_valid(self):
        self.assertEqual(st.validate_persona(st.persona_template()), [])

    def test_missing_ambivalence_fails(self):
        # L4 ambivalence is the rumination engine — a core field, so its absence
        # is an error, not a tolerable omission.
        p = st.persona_template()
        del p["layers"]["L4_relationship_dynamics"]["ambivalence"]
        errors = st.validate_persona(p)
        self.assertTrue(any("ambivalence" in e for e in errors))

    def test_missing_layer_fails(self):
        p = st.persona_template()
        del p["layers"]["L2_voice"]
        errors = st.validate_persona(p)
        self.assertTrue(any("L2_voice" in e for e in errors))

    def test_non_object_fails(self):
        self.assertTrue(st.validate_persona("not a dict"))


class TestPersonaIO(StateTestCase):
    """save/load/list are the single on-disk path for personas (issue 02). The
    write must validate at the boundary so a broken persona never reaches the
    runner, and the round-trip must preserve the user's narration verbatim."""

    def test_save_persona_round_trips(self):
        p = st.persona_template("boss-kim")
        path = st.save_persona(self.dd, p)
        self.assertTrue(path.exists())
        self.assertEqual(path, self.dd / "personas" / "boss-kim.json")
        self.assertEqual(st.load_persona(self.dd, "boss-kim"), p)

    def test_save_persona_preserves_non_ascii_narration(self):
        # Narration is runtime data in the user's own language, stored as-is
        # (ensure_ascii=False). It must round-trip raw UTF-8, not \uXXXX escapes.
        # We assert this with a language-neutral accented string so the test
        # source itself stays ASCII (the plugin's English-source rule).
        name = "Señor Café"  # "Señor Café" — non-ASCII, no hardcoded locale
        p = st.persona_template("boss-kim")
        p["display_name"] = name
        path = st.save_persona(self.dd, p)
        self.assertIn(name, path.read_text(encoding="utf-8"))  # raw, not escaped
        self.assertEqual(st.load_persona(self.dd, "boss-kim")["display_name"], name)

    def test_save_persona_rejects_invalid(self):
        p = st.persona_template("boss-kim")
        del p["layers"]["L4_relationship_dynamics"]["ambivalence"]
        with self.assertRaises(ValueError) as ctx:
            st.save_persona(self.dd, p)
        self.assertIn("ambivalence", str(ctx.exception))
        # Rejected before any file is written — nothing lands on disk.
        self.assertEqual(st.list_personas(self.dd), [])

    def test_load_persona_none_when_absent(self):
        self.assertIsNone(st.load_persona(self.dd, "nobody"))

    def test_list_personas_empty_when_no_dir(self):
        self.assertEqual(st.list_personas(self.dd), [])

    def test_list_personas_sorted(self):
        # Multi-persona = several files in one dir; list them for collision
        # checks and runner selection.
        st.save_persona(self.dd, st.persona_template("boss-kim"))
        st.save_persona(self.dd, st.persona_template("mom"))
        st.save_persona(self.dd, st.persona_template("ex-jun"))
        self.assertEqual(st.list_personas(self.dd), ["boss-kim", "ex-jun", "mom"])


class TestRenderReminder(StateTestCase):
    """The hook->model contract. It must surface the fields the model reads
    instead of re-deriving from the conversation (the context-rot failure)."""

    def test_reminder_reports_core_fields(self):
        state = st.start_session(self.dd, persona_id="boss-kim")
        st.tick(state, "msg")
        text = st.render_reminder(state)
        self.assertIn("boss-kim", text)
        self.assertIn("stage: vent", text)
        self.assertIn("turn: 1", text)
        self.assertIn("distress guard: clear", text)

    def test_reminder_flags_hard_ceiling(self):
        state = st.new_session()
        state["turn"] = 11
        state["guards"] = st.evaluate_guards(state, "")
        self.assertIn("HARD CEILING", st.render_reminder(state))


class TestDataDirResolution(unittest.TestCase):
    """Precedence: explicit arg > SAY_IT_DATA_DIR > CLAUDE_PLUGIN_DATA; None when
    nothing is set so the hot path can bail instead of guessing a location."""

    def setUp(self):
        self._saved = {k: os.environ.get(k)
                       for k in ("SAY_IT_DATA_DIR", "CLAUDE_PLUGIN_DATA")}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_none_when_unset(self):
        self.assertIsNone(st.data_dir())

    def test_explicit_arg_wins(self):
        os.environ["SAY_IT_DATA_DIR"] = "/from/env"
        self.assertEqual(st.data_dir("/explicit"), Path("/explicit"))

    def test_say_it_dir_beats_plugin_data(self):
        os.environ["SAY_IT_DATA_DIR"] = "/dev/override"
        os.environ["CLAUDE_PLUGIN_DATA"] = "/prod"
        self.assertEqual(st.data_dir(), Path("/dev/override"))


if __name__ == "__main__":
    unittest.main()
