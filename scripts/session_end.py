#!/usr/bin/env python3
"""Deactivate the say-it session (closure or safety stop).

Flips active=false so the tick hook goes quiet again. The file is kept, not
deleted, so the final state stays inspectable. Saving the takeaway is a separate
step (save_takeaway.py) owned by the closure flow in issue 06.

Usage:
    session_end.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    dd = st.data_dir()
    if dd is None:
        print("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)", file=sys.stderr)
        return 1

    state = st.end_session(dd)
    if state is None:
        print("say-it: no session to end")
        return 0
    print(f"say-it session ended: persona={state.get('persona_id')} "
          f"turns={state.get('turn')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
