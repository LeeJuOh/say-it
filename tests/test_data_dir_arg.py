#!/usr/bin/env python3
"""Regression for the production data-dir resolution path (ADR 0005).

The bug this guards against: every script the model invokes over the Bash tool
resolved the data dir from ``os.environ`` only, but the Bash tool does NOT receive
the plugin's env vars (CLAUDE_PLUGIN_DATA) -- only hook/MCP/LSP subprocesses do.
In production the scripts therefore got no data dir and exited 1, killing the
whole session before it began.

The existing integration smoke could not catch it because it injects
SAY_IT_DATA_DIR into the subprocess env, exercising the env path that production
never has. These tests deliberately run with BOTH data-dir env vars stripped, so
the data dir can only arrive the way it does in production: as the substituted
``--data-dir "${CLAUDE_PLUGIN_DATA}"`` argument (a positional arg for the shell
wrapper). Any Korean stays in the lexicon corpus, never in this source.
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


def _bash_tool_env() -> dict:
    """The env a script actually sees under the Bash tool: the plugin data-dir
    vars are absent. Strip both so the only way to a data dir is the argument."""
    env = dict(os.environ)
    env.pop("SAY_IT_DATA_DIR", None)
    env.pop("CLAUDE_PLUGIN_DATA", None)
    return env


class DataDirFromArg(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dd = Path(self._tmp.name)
        self.env = _bash_tool_env()
        # Seed a persona straight through the library (explicit dd, no env needed).
        st.save_persona(self.dd, st.persona_template("boss-kim"))

    def tearDown(self):
        self._tmp.cleanup()

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

    # -- the production path: a whole round driven by --data-dir, no env ------- #
    def test_full_arc_via_arg_without_env(self):
        """The exact calling convention SKILL.md now uses (substituted
        ${CLAUDE_PLUGIN_DATA} -> --data-dir), with the env the Bash tool really
        has. Pre-fix this could not even parse --data-dir; it now must work."""
        d = str(self.dd)
        self._py("session_start.py", "--persona", "boss-kim", "--data-dir", d)
        self.assertTrue(st.load_session(self.dd)["active"])
        for nxt in ("role-swap", "integration", "closure"):
            self.assertEqual(self._sh(nxt, d).returncode, 0)
        self._py("save_takeaway.py", "--persona", "boss-kim", "--theme",
                 "boss/credit-theft", "--takeaway", "credit, not apology", "--data-dir", d)
        self._py("session_end.py", "--data-dir", d)
        self.assertFalse(st.load_session(self.dd)["active"])
        self.assertEqual(len(st.load_log(self.dd)["entries"]), 1)

    def test_save_persona_via_arg_without_env(self):
        draft = self.dd / "draft.json"
        draft.write_text(json.dumps(st.persona_template("mentor-lee")), encoding="utf-8")
        self._py("save_persona.py", "--file", str(draft), "--data-dir", str(self.dd))
        self.assertIn("mentor-lee", st.list_personas(self.dd))

    def test_save_correction_via_arg_without_env(self):
        self._py("save_correction.py", "--persona", "boss-kim", "--layer", "L2_voice",
                 "--note", "softer than that in real life", "--data-dir", str(self.dd))
        persona = st.load_persona(self.dd, "boss-kim")
        self.assertEqual(len(persona["corrections"]), 1)

    def test_session_block_via_arg_without_env(self):
        self._py("session_start.py", "--persona", "boss-kim", "--data-dir", str(self.dd))
        self._py("session_block.py", "--data-dir", str(self.dd))
        self.assertTrue(st.load_session(self.dd)["blocked"])

    # -- the failure is loud, not silent, when nothing supplies a data dir ----- #
    def test_scripts_exit_1_when_no_data_dir_anywhere(self):
        """No --data-dir and no env -> a clean exit 1 with a diagnostic, never a
        guess at a path. Covers a plain script and the shell wrapper."""
        res = self._py("session_end.py", expect_rc=1)
        self.assertIn("no data dir", res.stderr)
        res_sh = self._sh("role-swap", expect_rc=1)
        self.assertIn("no data dir", res_sh.stderr)

    # -- the shell wrapper still honours env when the arg is omitted ----------- #
    def test_transition_sh_falls_back_to_env_when_arg_omitted(self):
        """The data-dir arg is optional on the wrapper: omitted, it falls back to
        SAY_IT_DATA_DIR (st.data_dir precedence), which is how tests/dev drive it."""
        env = dict(self.env, SAY_IT_DATA_DIR=str(self.dd))
        self._py("session_start.py", "--persona", "boss-kim", "--data-dir", str(self.dd))
        res = subprocess.run([str(_SCRIPTS / "transition_stage.sh"), "role-swap"],
                             capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(st.load_session(self.dd)["stage"], "role-swap")


if __name__ == "__main__":
    unittest.main()
