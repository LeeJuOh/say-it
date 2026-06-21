# say-it

> **English** · [한국어](README.ko.md)

**Say the things you never got to say to a real person who still lives in your head — then put that one knot down.**

say-it is a Claude Code plugin that runs a structured *empty-chair* session. You face the person as *you carry them* — a boss, parent, partner, ex, friend you have unfinished business with — say what you never said, and set one knot down. It is a light, one-round ritual with guardrails against rumination, not therapy.

## What it is — and is not

- **Is:** one structured, four-stage round for a single living person you keep looping on, so you can finally say it and let it go.
- **Is *not* therapy, counseling, or medical care**, and not a substitute for them. There is no clinician and no diagnosis here. If what you carry is bigger than one round, that is a sign the right support is a professional, not a chatbot.
- **The person in the chair is not the real person.** The persona is *your internal model of someone* externalised so you have someone to say it to — not a faithful biography, and nothing it says is a verdict, apology, or forgiveness *from them*.

## How it works

Two skills, used in order:

1. **`/say-it-build`** — build the persona from *your own narration*. You describe the person in your words; the build fills gaps by extrapolating along the grain of what you said (no demographic or star-sign stereotypes). Narration only — no chat logs, screenshots, or DMs.
2. **`/say-it`** — run one session against that persona. Four stages, held on the rails by a per-turn hook:

| stage | what happens |
|---|---|
| **S1 · vent** | the persona shows up in their own voice and *receives* what you pour out |
| **S2 · role-swap** | you sit in the other chair and voice the other person yourself |
| **S3 · integration** | you return to your own seat — "so what did I actually want?" |
| **S4 · closure** | a takeaway in your own words, then the knot is set down and saved |

## Install

```
/plugin marketplace add LeeJuOh/say-it
/plugin install say-it@say-it
```

Then build a persona and run a session:

```
/say-it-build
/say-it
```

## Safety & guardrails

This session deliberately stirs up feelings you have kept down, so it carries guardrails:

- **Distress circuit-breaker.** If real distress surfaces — panic, or any thought of self-harm — the session **stops** and hands you a crisis line. Surfacing a crisis line is *duty of care*, not a contradiction of "this isn't therapy": it acknowledges a limit. The line shown is Korea's national 24/7 suicide-prevention counseling line, pulled live from a single source so it always matches what the session shows in the moment.
- **Revisit guard.** Looping back to the *same* knot is the rumination the product is built to interrupt. If you return to an issue you already worked, the guard gently mirrors that back and asks whether there is real progress — it does not block you.
- **Turn cap.** One round is one round, by design.

If you are in crisis right now, contact your local emergency services or a suicide-prevention line in your country immediately.

## Privacy

- **Narration only.** Your telling, in your own words, is what we model — never a raw chat log of the real person.
- **Local.** The persona, the live session state, and your saved takeaways are JSON files under the plugin's local data dir on your own machine. No server, no upload, no account.

## Not a fit

- **The deceased, or grief** — out of scope until the right safeguards exist.
- **Minors** — this is for adults working their own relationships.
- **As a weapon or a rehearsal for harm** — it is a place to put something *down*, not to sharpen a grievance into a plan.
- **As ongoing therapy or a daily dependency** — it is one round; the revisit guard will mirror daily looping back to you.

## License

[MIT](LICENSE) © 2026 LeeJuOh
