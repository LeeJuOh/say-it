#!/usr/bin/env python3
"""UserPromptSubmit hook entrypoint: the per-turn tick (ADR 0004).

Registered in hooks/hooks.json, so the harness runs this on EVERY user message
(UserPromptSubmit takes no matcher). The script gates itself on an *active*
say-it session, which is how "runs only while /say-it is active" is enforced
without a matcher: no active session_state, no output, instant exit.

When a session is active it:
  1. reads session_state.json,
  2. runs the guard checks (distress seam + turn-cap flags),
  3. increments the turn counter,
  4. persists the new state,
  5. injects an authoritative system-reminder describing the current state, so
     the model reads stage/turn/guards from a fresh source every turn instead of
     re-deriving them from a long conversation (context-rot, ADR 0004).

Contract: stdin is the hook event JSON; on exit 0 we print a JSON object whose
hookSpecificOutput.additionalContext becomes a <system-reminder> in the model's
context. We never block the prompt here — the tick observes and reports; any
stop decision is the model's, acting on the injected state.
"""

import json
import os
import sys

# scripts/ is not on sys.path when the harness runs us from the project dir,
# so add our own directory to import the sibling library.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sayit_state as st  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}

    dd = st.data_dir()
    if dd is None:
        return 0  # no data dir resolvable -> nothing to tick

    state = st.load_session(dd)
    if not state:
        return 0  # no say-it session at all -> stay silent (the gate)

    if state.get("blocked"):
        # Terminal safety hold from a prior acute-harm (Grade 2) trigger. Don't tick
        # or resume: re-inject the hold every turn so the conversation can't drift
        # back into the session (defense in depth with session_start's entry-refusal).
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": st.render_safety_hold(state),
            },
            "suppressOutput": True,
        }
        print(json.dumps(output, ensure_ascii=False))
        return 0

    if not state.get("active"):
        return 0  # session ended normally -> stay silent (the gate)

    prompt = event.get("prompt", "") or ""
    if event.get("session_id") and not state.get("session_id"):
        state["session_id"] = event["session_id"]

    st.tick(state, prompt)
    st.save_session(dd, state)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": st.render_reminder(state),
        },
        "suppressOutput": True,
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never let a tick error erase the user's prompt
        # Non-blocking: print to stderr, exit non-2 so the prompt still goes through.
        print(f"say-it tick hook error: {exc}", file=sys.stderr)
        sys.exit(0)
