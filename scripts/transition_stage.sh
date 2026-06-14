#!/usr/bin/env bash
# transition_stage.sh — forward-only stage transition (and the one-time vent
# extension) for a live say-it session. Model-invoked at the cap or stage end.
#
# This is a THIN wrapper, on purpose. The forward-only validation, the +3
# extension latch, and the state write all live in scripts/sayit_state.py, which
# is unit-tested with zero dependencies. The shell only parses one argument and
# shells out — the same dumb-CLI / tested-core split issues 01-03 used, so there
# is no logic here that a test cannot reach.
#
# Usage:
#   transition_stage.sh <next-stage>   # vent -> role-swap -> integration -> closure (forward only)
#   transition_stage.sh extend         # spend the one-time +3 vent extension past the soft cap
#
# On a rejected move (backward, skip, unknown stage, extension already used, no
# active session) the library raises and we exit 1 with its message on stderr, so
# the model can read why and correct rather than land in a wrong stage.
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: transition_stage.sh <vent|role-swap|integration|closure|extend>" >&2
  exit 2
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# argv into python -c: [0]='-c', [1]=script dir, [2]=the requested move.
exec python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import sayit_state as st

dd = st.data_dir()
if dd is None:
    sys.stderr.write("say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)\n")
    sys.exit(1)

arg = sys.argv[2]
try:
    if arg == "extend":
        state = st.use_extension(dd)
        hard = state.get("guards", {}).get("turn_cap", {}).get("hard")
        print("say-it: vent extension granted (turn " + str(state.get("turn")) +
              ", running to hard ceiling " + str(hard) + ")")
    else:
        state = st.advance_stage(dd, arg)
        print("say-it: stage -> " + str(state.get("stage")))
except ValueError as exc:
    sys.stderr.write("say-it: " + str(exc) + "\n")
    sys.exit(1)
' "$here" "$1"
