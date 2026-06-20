#!/usr/bin/env python3
"""Append a takeaway to the across-session log. Called by the model at closure.

ADR 0004 splits the takeaway log's access: the hook only READS it (entry-time
revisit matching); WRITING goes through this script, invoked by the model at
closure bit 4 once the label and takeaway are confirmed. The takeaway is stored
RAW (no summarizing) so same-issue similarity stays accurate.

Issue 01 owns the schema and the append mechanism (here); issue 06 owns the
closure UX that decides *what* label/takeaway to pass in.

Usage:
    save_takeaway.py --persona <id> --theme <label> --takeaway <text> [--session <id>]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a takeaway to the log.")
    parser.add_argument("--persona", required=True)
    parser.add_argument("--theme", required=True, help="confirmed theme label, e.g. boss/credit-theft")
    parser.add_argument("--takeaway", required=True, help="the takeaway in the user's own words, raw")
    parser.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    parser.add_argument("--data-dir", default=None,
                        help="persistent data dir; skills pass ${CLAUDE_PLUGIN_DATA} from "
                             "skill content. The Bash tool does not receive plugin env vars, "
                             "so this arrives as a substituted argument, not from env (ADR 0005).")
    args = parser.parse_args()

    dd = st.data_dir(args.data_dir)
    if dd is None:
        print("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)", file=sys.stderr)
        return 1

    log = st.append_takeaway(dd, persona_id=args.persona, theme_label=args.theme,
                             takeaway=args.takeaway, session_id=args.session)
    print(f"say-it takeaway saved: {args.persona} / {args.theme} "
          f"({len(log['entries'])} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
