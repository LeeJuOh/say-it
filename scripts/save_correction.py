#!/usr/bin/env python3
"""Append a persona correction ('the real person isn't like that'). Called by the
model during or after a session when the user pushes back on how the persona
behaved.

Non-destructive (issue 08): this only grows the persona's append-only
``corrections`` log; the built L0..L4 layers are never overwritten, so the drift
toward the user's actual perception stays auditable across sessions. The note is
the user's runtime data, stored RAW (no summarizing/normalizing).

State logic lives in ``sayit_state.append_correction``; this is the thin CLI seam
the model invokes, mirroring ``save_takeaway.py``.

Usage:
    save_correction.py --persona <id> --layer <L0..L4> --note <text>
                       [--before <text>] [--after <text>]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a persona correction.")
    parser.add_argument("--persona", required=True)
    parser.add_argument("--layer", required=True, choices=list(st._PERSONA_LAYERS),
                        help="which layer the correction targets, e.g. L2_voice")
    parser.add_argument("--note", required=True,
                        help="what the user says is wrong, in their own words, raw")
    parser.add_argument("--before", help="the persona's current behaviour (optional)")
    parser.add_argument("--after", help="how the user says it should be (optional)")
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
        persona = st.append_correction(dd, persona_id=args.persona, layer=args.layer,
                                       note=args.note, before=args.before, after=args.after)
    except ValueError as e:
        print(f"say-it: {e}", file=sys.stderr)
        return 1

    n = len(persona.get("corrections", []))
    print(f"say-it correction saved: {args.persona} / {args.layer} ({n} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
