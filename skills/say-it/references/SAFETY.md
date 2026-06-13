# Safety — distress circuit-breaker (STUB)

> **Status: placeholder.** This slice (issue 01) only wires the safety *seam* in
> code so the deterministic floor has a home; the full safety content — the
> Korean-locale detection keywords, the tiered response copy, and the escalation
> wording — is owned by **[issue 10](../../../docs/issues/10-safety-disclosure.md)**. Do not
> treat the brief notes below as the complete policy.

## Why a hard floor exists (ADR 0003)

Safety detection is two-layered, and the split is deliberate
([ADR 0003](../../../docs/adr/0003-safety-stop-hard-gate.md)):

- **HARD floor** — code-level regex in `scripts/sayit_state.py`
  (`check_distress` / `DISTRESS_PATTERNS`). Runs every turn on the hook, fires on
  obvious signals unconditionally, and the model cannot talk its way past it. A
  prompt-only safety net is forbidden, because a long conversation can drift the
  model off its instructions exactly when it matters most.
- **SOFT augment** — prompt-level guidance layered *on top of* the floor for
  variation and context. It strengthens the floor; it never replaces it.

In issue 01 the floor is wired but empty: `DISTRESS_PATTERNS = []`. The call site
is done so issue 07 only supplies the regexes and tier routing without touching
the plumbing.

## The two tiers

The distress circuit-breaker is separate from the anti-rumination turn cap — that
cap is about looping, this is about acute harm. When it triggers, the session
stops immediately:

1. **panic** — general acute distress → de-escalate / wind the session down.
2. **acute-harm** — self-harm or crisis signals → surface a crisis hotline and do
   **not** resume the session.

The authoritative state block the hook injects each turn already carries this
contract (see `render_reminder`): if the distress guard is TRIGGERED, the model
follows the safety path regardless of the current stage.

## What issue 10 ([10-safety-disclosure](../../../docs/issues/10-safety-disclosure.md)) still owns

- The actual Korean detection keywords / regexes (and their tier assignment).
- The exact response copy for each tier, including the crisis-hotline resources.
- Any locale or jurisdiction handling for those resources.
