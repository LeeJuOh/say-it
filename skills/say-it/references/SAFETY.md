# say-it — safety notice

> **Audience: the user.** This is the one-page safety disclosure the user should be
> able to see up front and reach any time during a session. It is *source prose in
> English*, like the rest of the skill; the model **renders it to the user in their
> own language** (Korean) when surfacing it — the same way the persona voice and all
> session facilitation already work. Don't hardcode a translated copy here; that
> would split the source and trip the English-source gate.
>
> The runtime *mechanism* behind the crisis-line handling (how detection fires, the
> two grades, the BLOCKED latch) is the sibling
> [`distress-detection.md`](distress-detection.md) — that one is for the agent. This
> file is the static notice; the dynamic crisis-line surfacing is that mechanism's job.

## What say-it is — and is not

say-it is a **light, one-round ritual** for saying the things you never got to say
to a real person who still lives in your head. You build *the person as you carry
them* and run a structured four-stage session to put one knot down.

It is **not therapy, counseling, or medical care**, and it is not a substitute for
them. There is no clinician here and no diagnosis — it's one structured round, on
purpose. If what you're carrying is bigger than one round, that's not a failure of
the exercise; it's a sign the right support is a professional, not a chatbot.

## The person in the chair is not the real person

The persona you face is **your internal model of someone** — "the person as you
perceive them" — externalised so you have someone to say it to. It is not the real
person, not a faithful biography, and nothing it says is a verdict, an apology, or
forgiveness *from them*. You put down **this one knot** — never the person. They're
alive; whatever you do with the real them, if anything, stays yours to decide in
your own time.

## If it gets hard — the crisis line

This session deliberately stirs up feelings you've kept down. If, in the middle of
it, you find yourself in real distress — panic, or any thought of harming yourself —
**the session stops and hands you a crisis line.** That is duty of care, not a
contradiction of "this isn't therapy": surfacing a crisis line is exactly
*acknowledging a limit* — "this isn't our domain; here is who can help."

The crisis line shown is Korea's national suicide-prevention counseling line,
available 24/7. When this notice is surfaced, the exact number is pulled live from
the one shared crisis-line source, so what you see always matches what the session
itself would show you in the moment.

## What we do with your words (narration only, kept local)

- **Narration only.** You describe the person *in your own words*. We do not ask
  for, accept, or read chat logs, KakaoTalk exports, screenshots, or DMs — your
  telling is the perception we want; a raw log is the real person, which is exactly
  what we are *not* modelling.
- **Local.** The persona, the live session state, and your saved takeaways are JSON
  files under the plugin's local data dir on your own machine. There is no server,
  no upload, and no account in this skill stage.

Because we only ever hold *your* narration kept *locally*, the data risk is small —
which is why this is a **safety** notice (about emotional safety) rather than a data
-compliance contract.

## Use it for this — not for that

**A good fit:** a living person from your own life — a boss, parent, partner, ex,
friend — someone you have unfinished business with and keep looping on, where you
want to finally say it and set the knot down.

**Not a fit:**

- **The deceased, or grief.** Out of scope until the right crisis-and-sensitivity
  safeguards exist — planned for a later, safeguarded phase.
- **Minors.** This is for adults working their own relationships.
- **As a weapon or a rehearsal for harm.** It's a place to put something down, not
  to sharpen a grievance into a plan against a real person.
- **As ongoing therapy or a daily dependency.** It's one round. Looping back to the
  same knot every day is the rumination the whole product is built to interrupt; the
  revisit guard will gently mirror that back to you.

## What this notice is not (app-stage, out of scope)

This is a **notice / disclaimer / guide page**, not a contract. Formal Terms of
Service, PIPA de-identification, and any server-side storage belong to the hosting-
app stage, not this skill. When the product reaches that stage, this page is the
seed a formal legal review extends — it is not that review.

<!--
source notes (for maintainers; NOT part of the user-facing notice — the model
renders the prose above to the user and drops this block):
- Frame & scope (light one round, deceased/minors exclusion, app-stage ToS/PIPA):
  PRD (docs/prd/PRD.md).
- "the person as you perceive them", not the real person: reinforced at build
  preview and at S4 closure (bit 3).
- Narration-only input + local-only data: ADR 0002.
- Crisis line as duty-of-care that coexists with "not therapy", and the two-grade
  stop: ADR 0003. Runtime mechanism: distress-detection.md.
- The crisis line is a SINGLE SOURCE: lexicon/distress.ko.json (DISTRESS_HOTLINE),
  rendered via sayit_state.hotline_text(). Do NOT hardcode a second copy in this
  notice (issue 10, no-mismatch rule). Current value for human reference only
  (authoritative source = the lexicon): 109 — Korea's suicide-prevention line, 24/7.
-->

