#!/usr/bin/env python3
"""Validate and persist a persona built by /say-it-build.

The build skill assembles the 5-layer persona as JSON, writes it to a temp file
(or pipes it on stdin), then calls this to land it at
``$CLAUDE_PLUGIN_DATA/personas/<id>.json``. Routing the write through here (not a
raw file write from the skill) keeps ``validate_persona`` as the single gate:
the persona is checked exactly once, at the boundary, so a structurally-broken
file never reaches the session runner. On validation failure this prints the
errors and exits non-zero, which is the signal for the model to fix the JSON and
re-run rather than ship a bad persona.

Usage:
    save_persona.py --file <path-to-persona.json>
    save_persona.py --file -            # read JSON from stdin
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and save a persona.")
    parser.add_argument("--file", required=True,
                        help="path to the persona JSON, or '-' to read stdin")
    parser.add_argument("--data-dir", default=None,
                        help="persistent data dir; skills pass ${CLAUDE_PLUGIN_DATA} from "
                             "skill content. The Bash tool does not receive plugin env vars, "
                             "so this arrives as a substituted argument, not from env (ADR 0005).")
    args = parser.parse_args()

    dd = st.data_dir(args.data_dir)
    if dd is None:
        print("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)", file=sys.stderr)
        return 1

    try:
        raw = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    except OSError as exc:
        print(f"say-it: cannot read persona file: {exc}", file=sys.stderr)
        return 1

    try:
        persona = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"say-it: persona is not valid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        path = st.save_persona(dd, persona)
    except ValueError as exc:
        # Structural errors: surface them so the model can correct the layers.
        print(f"say-it: {exc}", file=sys.stderr)
        return 1

    print(f"say-it persona saved: {persona['id']} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
