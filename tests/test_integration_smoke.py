#!/usr/bin/env python3
"""End-to-end integration smoke (issue 09): drive a whole say-it round through the
*real* CLI scripts the model invokes, across process boundaries, in one narrative.

The per-feature unit tests in ``test_state.py`` already lock the deterministic core
(tick, caps, distress, persona IO, corrections). What they do NOT prove is that the
scripts *wire together* into a clean build->S1->S2->S3->S4 walkthrough and that the
three guards still trip when reached through the actual CLI seam. That wiring is the
MVP capstone's mechanical half (issue 09); the tone/scaffolding half is a human
sign-off (see ``docs/evals/09-integration-matrix.md``), which no test can stand in
for.

Each test gets its own tmp data dir via SAY_IT_DATA_DIR, so the throwaway-dir smoke
the close-out rhythm runs by hand is captured here as a repeatable regression. Any
Korean stays in the lexicon corpus (loaded at runtime), never in this source — the
Hangul gate covers tests/.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import sayit_state as st  # noqa: E402


def _acute_harm_text() -> str:
    """Pull a labelled acute-harm phrase from the shipped lexicon corpus (issue 07).
    The corpus is the spec; we drive the distress guard with the real signal rather
    than hardcoding Korean into this (gated) source."""
    corpus = json.loads((st._lexicon_dir() / "distress_examples.ko.json").read_text(encoding="utf-8"))["cases"]
    return next(c["text"] for c in corpus if c["expect"] == "acute-harm")


class IntegrationSmoke(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dd = Path(self._tmp.name)
        self.env = dict(os.environ, SAY_IT_DATA_DIR=str(self.dd))
        # Build leaves a persona on disk; seed one the way save_persona would.
        st.save_persona(self.dd, st.persona_template("boss-kim"))

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers: invoke the same CLIs the model calls ----------------------- #
    def _py(self, script, *args, expect_rc=0):
        res = subprocess.run([sys.executable, str(_SCRIPTS / script), *args],
                             capture_output=True, text=True, env=self.env)
        if expect_rc is not None:
            self.assertEqual(res.returncode, expect_rc,
                             f"{script} {args} -> rc={res.returncode}\n{res.stderr}")
        return res

    def _sh(self, *args, expect_rc=0):
        res = subprocess.run([str(_SCRIPTS / "transition_stage.sh"), *args],
                             capture_output=True, text=True, env=self.env)
        if expect_rc is not None:
            self.assertEqual(res.returncode, expect_rc,
                             f"transition {args} -> rc={res.returncode}\n{res.stderr}")
        return res

    def _tick(self, prompt):
        """Fire the UserPromptSubmit hook the way the harness does and return the
        injected reminder text (or "" if the hook stayed silent)."""
        res = subprocess.run([sys.executable, str(_SCRIPTS / "tick.py")],
                             input=json.dumps({"prompt": prompt}),
                             capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, res.stderr)
        if not res.stdout.strip():
            return ""
        return json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]

    # -- the happy path: a whole round, no errors --------------------------- #
    def test_full_arc_completes_without_error(self):
        self._py("session_start.py", "--persona", "boss-kim")
        # S1 vent: a couple of pour-it-out turns, hook ticks each.
        self.assertIn("stage: vent", self._tick("he took credit again"))
        self.assertIn("turn: 2", self._tick("and said nothing in the meeting"))
        # S1 -> S2 -> S3 -> S4, forward only, each transition accepted.
        for nxt in ("role-swap", "integration", "closure"):
            self.assertEqual(self._sh(nxt).returncode, 0)
        # S4 closure: file the takeaway, then force-close.
        self._py("save_takeaway.py", "--persona", "boss-kim",
                 "--theme", "boss/credit-theft", "--takeaway", "I wanted the credit, not an apology.")
        self._py("session_end.py")
        # The round is over: session inactive, takeaway persisted, stage reached closure.
        state = st.load_session(self.dd)
        self.assertFalse(state["active"])
        self.assertEqual(state["stage"], "closure")
        self.assertEqual(len(st.load_log(self.dd)["entries"]), 1)

    # -- guard 1: the vent turn cap (soft invite -> extension -> hard ceiling) #
    def test_turn_cap_guard_trips(self):
        self._py("session_start.py", "--persona", "boss-kim")
        last = ""
        for i in range(8):  # DEFAULT_SOFT_CAP = 8
            last = self._tick(f"venting turn {i}")
        self.assertIn("CAP_TRIGGERED: SOFT", last)          # soft invite at 8
        self._sh("extend")                                   # spend the one-time +3
        self.assertIn("extension already used", self._sh("extend", expect_rc=1).stderr)
        for i in range(3):  # climb to the hard ceiling (11)
            last = self._tick(f"more {i}")
        self.assertIn("CAP_TRIGGERED: HARD", last)           # hard ceiling is non-negotiable

    # -- guard 2: the distress circuit-breaker (acute-harm latches, no resume) #
    def test_distress_guard_latches_and_refuses_resume(self):
        self._py("session_start.py", "--persona", "boss-kim")
        self._tick("he took credit again")
        # An acute-harm signal must latch the session BLOCKED in code, not depend on
        # the model choosing to stop.
        self._tick(_acute_harm_text())
        self.assertTrue(st.load_session(self.dd)["blocked"])
        # Next turn re-injects the safety hold instead of ticking on.
        held = self._tick("are you still there")
        self.assertIn("SAFETY HOLD", held)
        self.assertIn(st.DISTRESS_HOTLINE["number"], held)
        # And a fresh start is refused (exit 2 = safety refusal) with the hotline.
        res = self._py("session_start.py", "--persona", "boss-kim", expect_rc=2)
        self.assertIn(st.DISTRESS_HOTLINE["number"], res.stderr)

    # -- guard 3: the revisit guard (same person + same knot = prior surfaces) #
    def test_revisit_guard_surfaces_prior_takeaway(self):
        # First round leaves a filed takeaway.
        self._py("session_start.py", "--persona", "boss-kim")
        for nxt in ("role-swap", "integration", "closure"):
            self._sh(nxt)
        self._py("save_takeaway.py", "--persona", "boss-kim",
                 "--theme", "boss/credit-theft", "--takeaway", "credit, not apology")
        self._py("session_end.py")
        # Same person + same knot = the revisit lookup the entry check reads must hit;
        # a different knot for the same person must not (legit revisit, not exile).
        self.assertEqual(len(st.find_revisit(self.dd, "boss-kim", "boss/credit-theft")), 1)
        self.assertEqual(st.find_revisit(self.dd, "boss-kim", "boss/micromanaging"), [])

    # -- entry safety notice (issue 10): the single source exists and is wired  #
    def test_safety_notice_source_is_live(self):
        # The build-entry notice is model-rendered prose, but it routes through one
        # source (hotline_text). Prove the source is populated and the build skill
        # actually invokes it once at entry, so the "shown at entry" acceptance has a
        # mechanical floor under the human's visual check.
        self.assertTrue(st.hotline_text())
        build = (_ROOT / "skills" / "say-it-build" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("one-time safety notice", build)
        self.assertIn("hotline_text()", build)


if __name__ == "__main__":
    unittest.main()
