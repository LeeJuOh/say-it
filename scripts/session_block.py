#!/usr/bin/env python3
"""Latch the say-it session BLOCKED (terminal safety hold) and stop it.

The HARD keyword floor latches this automatically inside the hook tick when its
regexes catch an acute-harm signal. This CLI is the SOFT-layer counterpart: when
the *model* recognizes an acute self-harm signal the keyword floor missed (an
oblique phrasing, a somatic crisis), it calls this so the same resume-refusal
holds — the tick hook re-injects the hold and session_start refuses a new round.
Without it, SOFT-detected harm would end the session but leave it resumable, a
gap between the two detection layers ADR 0003 deliberately pairs.

Usage:
    session_block.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Latch the say-it session BLOCKED (safety hold).")
    parser.add_argument("--data-dir", default=None,
                        help="persistent data dir; skills pass ${CLAUDE_PLUGIN_DATA} from "
                             "skill content. The Bash tool does not receive plugin env vars, "
                             "so this arrives as a substituted argument, not from env (ADR 0005).")
    args = parser.parse_args()

    dd = st.data_dir(args.data_dir)
    if dd is None:
        print("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)", file=sys.stderr)
        return 1

    state = st.block_session(dd)
    if state is None:
        print("say-it: no session to block")
        return 0
    print(f"say-it session BLOCKED (safety hold): persona={state.get('persona_id')} "
          f"turns={state.get('turn')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
