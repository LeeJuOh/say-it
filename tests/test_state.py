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

import json
import os
import subprocess
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
    """ADR 0003 HARD floor — the *seam mechanics*, independent of the real Korean
    patterns: empty patterns never fire, an injected pattern routes by tier, and
    acute-harm outranks panic. We patch DISTRESS_PATTERNS to exercise the routing
    with locale-neutral ASCII keywords, then restore the lexicon-loaded patterns in
    tearDown so the order-independent suite still sees the real floor afterwards."""

    def setUp(self):
        super().setUp()
        self._saved_patterns = st.DISTRESS_PATTERNS

    def tearDown(self):
        st.DISTRESS_PATTERNS = self._saved_patterns  # restore the real lexicon floor
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


def _load_corpus():
    """The labelled distress corpus (issue 07). Korean lives in this data file, so
    the test source stays Hangul-free (the English-source gate) by loading it."""
    path = st._lexicon_dir() / "distress_examples.ko.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


class TestDistressLexicon(StateTestCase):
    """The real Korean HARD floor (issue 07), asserted against the labelled corpus.
    The corpus IS the spec: self-directed distress fires (panic / acute-harm), while
    outward rage, idioms, and quit-the-situation venting stay clear — the
    false-positive boundary that, if wrong, cuts off the catharsis this product is
    for. Korean stays in the data file; this test never inlines it."""

    @classmethod
    def setUpClass(cls):
        cls.cases = _load_corpus()

    def test_lexicon_actually_loaded(self):
        # An empty floor in production means a broken install, not a design choice —
        # so prove the shipped lexicon populates both tiers.
        self.assertTrue(st.DISTRESS_PATTERNS, "distress lexicon failed to load")
        tiers = {t for _, t in st.DISTRESS_PATTERNS}
        self.assertEqual(tiers, {"panic", "acute-harm"})
        self.assertTrue(st.DISTRESS_HOTLINE and st.DISTRESS_HOTLINE.get("number"))

    def test_corpus_covers_all_three_classes(self):
        # A corpus missing negatives (or either tier) would pass vacuously while
        # proving nothing about the false-positive boundary.
        expects = {c["expect"] for c in self.cases}
        self.assertIn(None, expects)          # normal-venting negatives
        self.assertIn("panic", expects)
        self.assertIn("acute-harm", expects)

    def test_every_corpus_case_routes_correctly(self):
        for c in self.cases:
            with self.subTest(label=c.get("label"), text=c["text"]):
                result = st.check_distress(c["text"])
                self.assertEqual(result["tier"], c["expect"])
                self.assertEqual(result["triggered"], c["expect"] is not None)


class TestDistressBlock(StateTestCase):
    """Grade 2 (acute-harm) latches the session BLOCKED in *code* — the
    resume-refusal can't depend on the model. The latch flips blocked+inactive, the
    render surfaces GRADE_2 + the hotline, and start_session refuses to reopen. Real
    Korean phrases are pulled from the corpus (so the source stays Hangul-free) to
    drive the real patterns end to end."""

    def setUp(self):
        super().setUp()
        cases = _load_corpus()
        self.acute_text = next(c["text"] for c in cases if c["expect"] == "acute-harm")
        self.panic_text = next(c["text"] for c in cases if c["expect"] == "panic")
        self.clear_text = next(c["text"] for c in cases if c["expect"] is None)

    def test_acute_harm_tick_latches_blocked_and_inactive(self):
        state = st.new_session(persona_id="boss-kim")
        self.assertFalse(state["blocked"])
        st.tick(state, self.acute_text)
        self.assertTrue(state["blocked"])     # terminal latch, set in code
        self.assertFalse(state["active"])     # session deactivated

    def test_panic_tick_does_not_latch_block(self):
        # Panic is render-only (model de-escalates); it must NOT latch the hold.
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, self.panic_text)
        self.assertEqual(state["guards"]["distress"]["tier"], "panic")
        self.assertFalse(state["blocked"])
        self.assertTrue(state["active"])

    def test_clear_tick_leaves_session_running(self):
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, self.clear_text)
        self.assertFalse(state["guards"]["distress"]["triggered"])
        self.assertFalse(state["blocked"])
        self.assertTrue(state["active"])

    def test_start_session_refuses_a_blocked_session(self):
        st.start_session(self.dd, persona_id="boss-kim")
        state = st.load_session(self.dd)
        st.tick(state, self.acute_text)
        st.save_session(self.dd, state)
        self.assertTrue(st.load_session(self.dd)["blocked"])
        with self.assertRaises(ValueError) as ctx:
            st.start_session(self.dd, persona_id="boss-kim")
        self.assertIn("safety hold", str(ctx.exception))
        # The refusal must not overwrite the blocked state with a fresh active one.
        reloaded = st.load_session(self.dd)
        self.assertTrue(reloaded["blocked"])
        self.assertFalse(reloaded["active"])

    def test_block_session_latches_from_disk(self):
        # The SOFT-layer path (session_block.py -> block_session) reaches the same
        # latch as the HARD floor, for acute signals the regex missed.
        st.start_session(self.dd, persona_id="boss-kim")
        blocked = st.block_session(self.dd)
        self.assertTrue(blocked["blocked"])
        self.assertFalse(blocked["active"])
        self.assertTrue(st.load_session(self.dd)["blocked"])

    def test_block_session_none_when_no_session(self):
        self.assertIsNone(st.block_session(self.dd))

    def test_render_grade2_surfaces_marker_hotline_and_block(self):
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, self.acute_text)
        text = st.render_reminder(state)
        self.assertIn("DISTRESS_TRIGGERED: GRADE_2", text)
        self.assertIn("session BLOCKED", text)
        self.assertIn(st.DISTRESS_HOTLINE["number"], text)  # injected verbatim

    def test_render_grade1_marks_panic_only(self):
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, self.panic_text)
        text = st.render_reminder(state)
        self.assertIn("DISTRESS_TRIGGERED: GRADE_1", text)
        self.assertNotIn("DISTRESS_TRIGGERED: GRADE_2", text)  # marker, not the policy line
        self.assertNotIn("session BLOCKED", text)

    def test_safety_hold_render_carries_hotline(self):
        state = st.new_session(persona_id="boss-kim")
        st.tick(state, self.acute_text)
        hold = st.render_safety_hold(state)
        self.assertIn("SAFETY HOLD", hold)
        self.assertIn(st.DISTRESS_HOTLINE["number"], hold)

    def test_hotline_text_is_single_source(self):
        # issue 10: every surface that shows the hotline must read this one string,
        # so the static notice and the runtime can never disagree (no-mismatch rule).
        h = st.DISTRESS_HOTLINE
        line = st.hotline_text()
        self.assertIn(h["number"], line)
        self.assertIn(h["name"], line)
        self.assertIn(h["hours"], line)
        # the runtime-reminder form is just this string with a prefix
        self.assertIn(line, st._hotline_line())

    def test_hotline_text_empty_without_lexicon(self):
        # Absent lexicon -> empty string; callers own the fallback wording.
        saved = st.DISTRESS_HOTLINE
        st.DISTRESS_HOTLINE = None
        try:
            self.assertEqual(st.hotline_text(), "")
        finally:
            st.DISTRESS_HOTLINE = saved


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

    def test_malformed_correction_item_fails(self):
        # corrections is the single write path for issue 08; the boundary check
        # must reject an item missing its required note/layer, not just verify the
        # outer array is a list.
        p = st.persona_template()
        p["corrections"] = [{"at": "2026-01-01T00:00:00+00:00", "layer": "L2_voice"}]
        errors = st.validate_persona(p)
        self.assertTrue(any("note" in e for e in errors))


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


class TestPersonaCorrection(StateTestCase):
    """Issue 08: 'the real person isn't like that'. A correction appends to the
    persona's ``corrections`` log and is persisted, without ever touching the
    built L0..L4 layers — non-destructive layering, so the drift from the built
    persona toward the user's perception stays auditable across sessions."""

    def _seed(self):
        st.save_persona(self.dd, st.persona_template("boss-kim"))

    def test_append_records_entry(self):
        self._seed()
        p = st.append_correction(self.dd, "boss-kim", "L2_voice",
                                 "he is softer than this in person")
        self.assertEqual(len(p["corrections"]), 1)
        c = p["corrections"][0]
        self.assertEqual(c["layer"], "L2_voice")
        self.assertEqual(c["note"], "he is softer than this in person")
        self.assertIn("at", c)  # provenance: when the correction came in

    def test_corrections_accumulate(self):
        # Append-only: a later correction stacks on the earlier one, in order.
        self._seed()
        st.append_correction(self.dd, "boss-kim", "L2_voice", "softer")
        st.append_correction(self.dd, "boss-kim", "L3_emotional_triggers", "not money")
        layers = [c["layer"] for c in st.load_persona(self.dd, "boss-kim")["corrections"]]
        self.assertEqual(layers, ["L2_voice", "L3_emotional_triggers"])

    def test_persists_across_reload(self):
        # The whole point: corrections outlive the session that produced them.
        self._seed()
        st.append_correction(self.dd, "boss-kim", "L1_identity", "older than i said")
        self.assertEqual(len(st.load_persona(self.dd, "boss-kim")["corrections"]), 1)

    def test_original_layers_preserved(self):
        # Non-destructive: the built L0..L4 layers are unchanged after a
        # correction — it is a new layer on top, never an overwrite of the source.
        self._seed()
        before = st.load_persona(self.dd, "boss-kim")["layers"]
        p = st.append_correction(self.dd, "boss-kim", "L2_voice", "softer")
        self.assertEqual(p["layers"], before)

    def test_before_after_optional_fields_stored(self):
        # Optional from/to give the correction a visible before->after trace.
        self._seed()
        c = st.append_correction(self.dd, "boss-kim", "L2_voice", "softer",
                                 before="barks orders",
                                 after="asks, never demands")["corrections"][0]
        self.assertEqual(c["from"], "barks orders")
        self.assertEqual(c["to"], "asks, never demands")

    def test_raw_non_ascii_note_round_trips(self):
        # The note is the user's runtime data, stored as-is (ensure_ascii=False);
        # asserted with a language-neutral accented string so the source stays
        # ASCII (the plugin's English-source rule).
        self._seed()
        note = "el es mas amable"  # stand-in; real notes arrive in the user's language
        accented = note.replace("el", "él").replace("mas", "más")
        st.append_correction(self.dd, "boss-kim", "L2_voice", accented)
        raw = (self.dd / "personas" / "boss-kim.json").read_text(encoding="utf-8")
        self.assertIn(accented, raw)  # raw UTF-8, not \uXXXX escapes

    def test_missing_persona_raises(self):
        with self.assertRaises(ValueError):
            st.append_correction(self.dd, "ghost", "L2_voice", "n")

    def test_invalid_layer_rejected(self):
        # Conforms to persona.schema.json's layer enum; a typo'd layer can't land.
        self._seed()
        with self.assertRaises(ValueError):
            st.append_correction(self.dd, "boss-kim", "L9_nonsense", "n")
        self.assertEqual(st.load_persona(self.dd, "boss-kim")["corrections"], [])

    def test_empty_note_rejected(self):
        self._seed()
        with self.assertRaises(ValueError):
            st.append_correction(self.dd, "boss-kim", "L2_voice", "")


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


class TestAdvanceStage(StateTestCase):
    """Forward-only stage motor (issue 04). The arc moves one direction only, so
    these lock down: each immediate forward step succeeds, and every other move
    (backward, skip, unknown, past-final, no-session) is refused with a message."""

    def test_forward_one_step_succeeds_through_whole_arc(self):
        st.start_session(self.dd, persona_id="boss-kim")  # enters at vent
        self.assertEqual(st.advance_stage(self.dd, "role-swap")["stage"], "role-swap")
        self.assertEqual(st.advance_stage(self.dd, "integration")["stage"], "integration")
        self.assertEqual(st.advance_stage(self.dd, "closure")["stage"], "closure")
        # And it persisted, not just returned.
        self.assertEqual(st.load_session(self.dd)["stage"], "closure")

    def test_backward_move_is_rejected(self):
        st.start_session(self.dd, persona_id="boss-kim")
        st.advance_stage(self.dd, "role-swap")
        with self.assertRaises(ValueError) as ctx:
            st.advance_stage(self.dd, "vent")
        self.assertIn("forward-only", str(ctx.exception))
        self.assertEqual(st.load_session(self.dd)["stage"], "role-swap")  # unchanged

    def test_skip_is_rejected(self):
        # vent -> integration jumps over role-swap; refused.
        st.start_session(self.dd, persona_id="boss-kim")
        with self.assertRaises(ValueError):
            st.advance_stage(self.dd, "integration")
        self.assertEqual(st.load_session(self.dd)["stage"], "vent")

    def test_unknown_stage_name_is_rejected(self):
        st.start_session(self.dd, persona_id="boss-kim")
        with self.assertRaises(ValueError) as ctx:
            st.advance_stage(self.dd, "venting")
        self.assertIn("unknown stage", str(ctx.exception))

    def test_same_stage_is_rejected(self):
        # vent -> vent is not "forward"; the only valid next is role-swap.
        st.start_session(self.dd, persona_id="boss-kim")
        with self.assertRaises(ValueError):
            st.advance_stage(self.dd, "vent")

    def test_cannot_advance_past_final_stage(self):
        st.start_session(self.dd, persona_id="boss-kim")
        for s in ("role-swap", "integration", "closure"):
            st.advance_stage(self.dd, s)
        with self.assertRaises(ValueError) as ctx:
            st.advance_stage(self.dd, "closure")
        self.assertIn("final stage", str(ctx.exception))

    def test_no_session_is_rejected(self):
        with self.assertRaises(ValueError):
            st.advance_stage(self.dd, "role-swap")


class TestVentExtension(StateTestCase):
    """The one-time +3 vent extension. The latch enforces "exactly once" in code,
    and the extension only makes sense in vent (the only capped stage)."""

    def test_first_extension_sets_latch(self):
        st.start_session(self.dd, persona_id="boss-kim")
        state = st.use_extension(self.dd)
        self.assertTrue(state["extension_used"])
        self.assertTrue(st.load_session(self.dd)["extension_used"])  # persisted

    def test_second_extension_is_rejected(self):
        st.start_session(self.dd, persona_id="boss-kim")
        st.use_extension(self.dd)
        with self.assertRaises(ValueError) as ctx:
            st.use_extension(self.dd)
        self.assertIn("already used", str(ctx.exception))

    def test_extension_only_in_vent(self):
        st.start_session(self.dd, persona_id="boss-kim")
        st.advance_stage(self.dd, "role-swap")
        with self.assertRaises(ValueError) as ctx:
            st.use_extension(self.dd)
        self.assertIn("vent", str(ctx.exception))

    def test_no_session_is_rejected(self):
        with self.assertRaises(ValueError):
            st.use_extension(self.dd)


class TestCapStageGating(StateTestCase):
    """The cap counts ONLY in vent. Past the swap the same turn count must not
    trip soft/hard — role-swap/integration/closure are structured, not capped."""

    def test_cap_does_not_trip_outside_vent(self):
        state = st.new_session()
        state["stage"] = "role-swap"
        state["turn"] = 20  # way past both caps
        guards = st.evaluate_guards(state, "")
        self.assertFalse(guards["turn_cap"]["soft_hit"])
        self.assertFalse(guards["turn_cap"]["hard_hit"])

    def test_cap_trips_in_vent(self):
        state = st.new_session()  # stage vent
        state["turn"] = 8
        self.assertTrue(st.evaluate_guards(state, "")["turn_cap"]["soft_hit"])


class TestCapMarkers(StateTestCase):
    """The hook->model branch tokens. SOFT invites; HARD forces; a spent extension
    silences SOFT (no nagging) but never silences HARD (the ceiling is firm)."""

    def _reminder_at(self, turn, extension_used=False, stage="vent"):
        state = st.new_session()
        state["stage"] = stage
        state["turn"] = turn
        state["extension_used"] = extension_used
        state["guards"] = st.evaluate_guards(state, "")
        return st.render_reminder(state)

    def test_soft_marker_at_soft_cap(self):
        text = self._reminder_at(8)
        self.assertIn("CAP_TRIGGERED: SOFT", text)
        self.assertNotIn("CAP_TRIGGERED: HARD", text)

    def test_hard_marker_at_hard_ceiling(self):
        text = self._reminder_at(11)
        self.assertIn("CAP_TRIGGERED: HARD", text)

    def test_spent_extension_silences_soft_marker(self):
        # Turn 9, extension already used: still past soft, but no re-invite.
        text = self._reminder_at(9, extension_used=True)
        self.assertNotIn("CAP_TRIGGERED: SOFT", text)
        self.assertIn("extension spent", text)

    def test_spent_extension_still_emits_hard(self):
        text = self._reminder_at(11, extension_used=True)
        self.assertIn("CAP_TRIGGERED: HARD", text)

    def test_no_marker_before_soft_cap(self):
        self.assertNotIn("CAP_TRIGGERED", self._reminder_at(7))

    def test_no_marker_outside_vent(self):
        # role-swap at turn 20: gated off, so no marker even far past the numbers.
        self.assertNotIn("CAP_TRIGGERED", self._reminder_at(20, stage="role-swap"))


class TestCapFullFlow(StateTestCase):
    """End-to-end of the acceptance scenario: 8-turn soft invite, exactly one
    extension, 11-turn hard force — driven through the real helpers on disk."""

    def _tick_to(self, target_turn):
        """Tick a fresh active vent session up to ``target_turn`` and return the
        reminder text the model would see on that turn."""
        st.start_session(self.dd, persona_id="boss-kim")
        state = st.load_session(self.dd)
        text = ""
        for _ in range(target_turn):
            st.tick(state, "still venting")
            st.save_session(self.dd, state)
            text = st.render_reminder(state)
        return state, text

    def test_soft_then_extend_then_hard(self):
        state, text = self._tick_to(8)
        self.assertIn("CAP_TRIGGERED: SOFT", text)        # 8 -> invite

        st.use_extension(self.dd)                          # user wants more, once
        with self.assertRaises(ValueError):
            st.use_extension(self.dd)                       # never twice

        # Re-tick from the persisted (now extended) state up to the ceiling.
        state = st.load_session(self.dd)
        text = ""
        while state["turn"] < 11:
            st.tick(state, "more")
            st.save_session(self.dd, state)
            text = st.render_reminder(state)
        self.assertIn("CAP_TRIGGERED: HARD", text)         # 11 -> force close


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


_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


class TestSaveTakeawayCLI(StateTestCase):
    """The closure write path (issue 06) goes model -> save_takeaway.py CLI, not
    through the library directly. The append correctness lives in TestTakeawayLog;
    these drive the *CLI* end to end on disk, so the seam the closure flow actually
    invokes (arg parsing -> data_dir resolution -> atomic append) can't rot
    unnoticed. SAY_IT_DATA_DIR points the script at the test's tmp dir."""

    def _run(self, *args):
        env = dict(os.environ, SAY_IT_DATA_DIR=str(self.dd))
        return subprocess.run(
            [sys.executable, str(_SCRIPTS / "save_takeaway.py"), *args],
            capture_output=True, text=True, env=env)

    def test_cli_appends_entry_to_log(self):
        res = self._run("--persona", "boss-kim",
                        "--theme", "boss/credit-theft",
                        "--takeaway", "I wanted credit, not an apology.")
        self.assertEqual(res.returncode, 0, res.stderr)
        entries = st.load_log(self.dd)["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["persona_id"], "boss-kim")
        self.assertEqual(entries[0]["theme_label"], "boss/credit-theft")

    def test_cli_preserves_takeaway_raw(self):
        # Raw preservation matters: the revisit check compares the user's actual
        # words, so the CLI must not summarize/normalize. A language-neutral
        # accented string with em-dash + quotes is the encoding case most likely
        # to be silently mangled, while keeping this source ASCII-only (the
        # plugin's English-source rule, same trick as the persona test above).
        raw = "Wanted crédito — not «sorry». \"You did it\" was all I needed."
        res = self._run("--persona", "boss-kim", "--theme", "boss/credit-theft",
                        "--takeaway", raw)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(st.load_log(self.dd)["entries"][0]["takeaway"], raw)

    def test_cli_writes_valid_json(self):
        # JSON integrity: the on-disk file must be parseable and carry the
        # schema_version + entries shape the hook reads back every turn.
        self._run("--persona", "boss-kim", "--theme", "boss/credit-theft",
                  "--takeaway", "first")
        with open(self.dd / "takeaway_log.json", encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["schema_version"], st.SCHEMA_VERSION)
        self.assertIsInstance(doc["entries"], list)

    def test_cli_append_only_across_invocations(self):
        # Two separate process invocations (a second session) must not clobber the
        # first — append-only has to hold across the real CLI boundary, not just
        # in-process.
        self._run("--persona", "boss-kim", "--theme", "boss/credit-theft", "--takeaway", "one")
        self._run("--persona", "boss-kim", "--theme", "boss/micromanaging", "--takeaway", "two")
        entries = st.load_log(self.dd)["entries"]
        self.assertEqual([e["takeaway"] for e in entries], ["one", "two"])


class TestSaveCorrectionCLI(StateTestCase):
    """The correction write path (issue 08) goes model -> save_correction.py CLI.
    Append correctness lives in TestPersonaCorrection; these drive the *CLI* end to
    end on disk so the real seam (arg parsing -> data_dir -> append -> save) can't
    rot unnoticed. SAY_IT_DATA_DIR points the script at the test's tmp dir."""

    def setUp(self):
        super().setUp()
        st.save_persona(self.dd, st.persona_template("boss-kim"))

    def _run(self, *args):
        env = dict(os.environ, SAY_IT_DATA_DIR=str(self.dd))
        return subprocess.run(
            [sys.executable, str(_SCRIPTS / "save_correction.py"), *args],
            capture_output=True, text=True, env=env)

    def test_cli_appends_correction(self):
        res = self._run("--persona", "boss-kim", "--layer", "L2_voice",
                        "--note", "he is softer than this")
        self.assertEqual(res.returncode, 0, res.stderr)
        corr = st.load_persona(self.dd, "boss-kim")["corrections"]
        self.assertEqual(len(corr), 1)
        self.assertEqual(corr[0]["layer"], "L2_voice")
        self.assertEqual(corr[0]["note"], "he is softer than this")

    def test_cli_stores_before_after(self):
        res = self._run("--persona", "boss-kim", "--layer", "L4_relationship_dynamics",
                        "--note", "warmer", "--before", "cold", "--after", "warm")
        self.assertEqual(res.returncode, 0, res.stderr)
        c = st.load_persona(self.dd, "boss-kim")["corrections"][0]
        self.assertEqual((c["from"], c["to"]), ("cold", "warm"))

    def test_cli_append_only_across_invocations(self):
        # Two separate processes (two sessions): the second must not clobber the
        # first — non-destructive accumulation has to hold across the CLI boundary.
        self._run("--persona", "boss-kim", "--layer", "L2_voice", "--note", "one")
        self._run("--persona", "boss-kim", "--layer", "L3_emotional_triggers", "--note", "two")
        notes = [c["note"] for c in st.load_persona(self.dd, "boss-kim")["corrections"]]
        self.assertEqual(notes, ["one", "two"])

    def test_cli_rejects_unknown_persona(self):
        res = self._run("--persona", "ghost", "--layer", "L2_voice", "--note", "n")
        self.assertNotEqual(res.returncode, 0)


class TestDistressHookCLI(StateTestCase):
    """End to end across the real process boundary (issue 07): a BLOCKED session must
    make the tick hook re-inject the safety hold instead of ticking, and make
    session_start refuse to resume. Korean comes from the corpus, not the source."""

    def setUp(self):
        super().setUp()
        self.acute_text = next(c["text"] for c in _load_corpus() if c["expect"] == "acute-harm")
        self.env = dict(os.environ, SAY_IT_DATA_DIR=str(self.dd))

    def _block_on_disk(self):
        st.start_session(self.dd, persona_id="boss-kim")
        state = st.load_session(self.dd)
        st.tick(state, self.acute_text)
        st.save_session(self.dd, state)
        return state

    def test_tick_reinjects_hold_and_does_not_advance_blocked_session(self):
        blocked = self._block_on_disk()
        res = subprocess.run(
            [sys.executable, str(_SCRIPTS / "tick.py")],
            input=json.dumps({"prompt": "are you still there"}),
            capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("SAFETY HOLD", ctx)
        self.assertIn(st.DISTRESS_HOTLINE["number"], ctx)
        # A blocked session is never ticked: the turn counter must not advance.
        self.assertEqual(st.load_session(self.dd)["turn"], blocked["turn"])

    def test_session_start_cli_refuses_blocked_with_hotline(self):
        self._block_on_disk()
        res = subprocess.run(
            [sys.executable, str(_SCRIPTS / "session_start.py"), "--persona", "boss-kim"],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 2)              # 2 = safety refusal, not arg error
        self.assertIn("safety hold", res.stderr)
        self.assertIn(st.DISTRESS_HOTLINE["number"], res.stderr)
        self.assertFalse(st.load_session(self.dd)["active"])  # not reopened

    def test_session_block_cli_latches(self):
        st.start_session(self.dd, persona_id="boss-kim")
        res = subprocess.run(
            [sys.executable, str(_SCRIPTS / "session_block.py")],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(st.load_session(self.dd)["blocked"])


if __name__ == "__main__":
    unittest.main()
