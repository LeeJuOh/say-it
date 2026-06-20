#!/usr/bin/env python3
"""Activate a say-it session. Invoked by /say-it at S1 (vent) entry.

Creating the active session_state here (not in the hook) is deliberate: it is the
gate that keeps the globally-firing tick hook silent in every conversation that
is NOT a say-it session. The hook only ticks while this file says active=true.

Usage:
    session_start.py --persona <id> [--session <session_id>] [--theme <label>]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate a say-it session.")
    parser.add_argument("--persona", required=True, help="persona id, matches personas/<id>.json")
    parser.add_argument("--session", default=os.environ.get("CLAUDE_SESSION_ID"),
                        help="Claude Code session id (optional)")
    parser.add_argument("--theme", default=None,
                        help="known issue theme label (optional; usually set at closure)")
    args = parser.parse_args()

    dd = st.data_dir()
    if dd is None:
        print("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)", file=sys.stderr)
        return 1

    try:
        state = st.start_session(dd, persona_id=args.persona,
                                 session_id=args.session, theme_label=args.theme)
    except ValueError as exc:
        # Safety hold: the prior session was stopped on an acute-harm (Grade 2)
        # signal and latched BLOCKED, so we refuse to open a fresh round on top of
        # it (ADR 0003 "no resume"). Surface the crisis hotline instead. Exit 2 so
        # the caller can tell a safety refusal from an arg/data-dir error (exit 1).
        msg = f"say-it: {exc}"
        line = st.hotline_text()
        if line:
            msg += f"\nsay-it crisis hotline: {line}"
        print(msg, file=sys.stderr)
        return 2
    print(f"say-it session started: persona={state['persona_id']} "
          f"stage={state['stage']} turn={state['turn']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
