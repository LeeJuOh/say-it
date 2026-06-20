---
name: say-it-build
description: >-
  Build the persona an empty-chair session runs against: interview the user about
  a specific real person who lives rent-free in their head (a boss, parent,
  partner, ex, friend) and write a 5-layer persona file. Use this whenever the
  user wants to set up, build, or describe the person they keep ruminating about
  before talking to them — "build a persona", "set up my boss for say-it",
  "I want to do an empty-chair thing with my mom", or any time they start
  describing someone they have unfinished business with and no persona exists
  yet. This is the BUILDER; running the session afterward is /say-it. It captures
  "the person as the user perceives them", not the real person.
---

# say-it-build — persona builder

This skill interviews the user about one real person and writes a persona file
that `/say-it` later runs an empty-chair session against. The persona is the
user's **internal object** — "the person as I perceive them" — externalised, not
a faithful biography. You build it from the user's own narration; the blanks you
fill, you fill along the grain of what they said.

Build and session are deliberately separate: this skill *only* builds. When the
persona is saved, tell the user they can start a session with `/say-it`.

## First thing: the one-time safety notice

Before you ask anything about the person — at the very start of a build, **once** —
surface the core safety notice. say-it deliberately stirs up suppressed feeling, and
the user is about to start describing someone they have unfinished business with, so
they should meet the frame before they pour anything in. Say it in your own warm
words (in the user's language), not as a wall of legalese, and fold in three things:

1. **This is a light one round, not therapy** — no clinician, no diagnosis; if what
   they're carrying is bigger than one round, the right support is a professional.
2. **The person you'll build is *the person as they perceive them*** — their internal
   model, not the real person, and nothing it later says is a verdict from the real one.
3. **If it gets hard, there's a crisis line.** Pull the exact number from the single
   source so this never drifts from the runtime one (issue 10, ADR 0003):

   ```bash
   python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts'); import sayit_state as st; print(st.hotline_text())"
   ```

Keep it to those three beats — this is the *core* notice, not the whole page. Point
the user at `../say-it/references/SAFETY.md` (the full one-page notice: limits, data,
appropriate vs forbidden uses, who it's for) if they want the rest, and **don't
repeat the notice every turn** — once at entry is the point; re-surfacing it mid-build
just adds friction.

## Say this framing out loud (and again at preview)

> "What we're building is the person **as you carry them in your head** — not the
> real them. If the real person is gentler or worse than this, that's fine; we're
> modelling your side of it so you have someone to say it to."

Why it matters: naming it as an internal object lowers the stakes (you're not
indicting a real human), keeps expectations honest (the bot will be *your*
version of them), and is the safety frame the whole product rests on.

## Input rule: narration only

The user describes the person **in their own words**. Do not ask for, accept, or
read KakaoTalk exports, chat logs, screenshots, or DMs — narration only (ADR
0002, permanent). If the user offers a log, decline and ask them to tell you in
their own words instead. Their telling *is* the perception we want; a raw log is
the real person, which is exactly what we are not modelling.

## The build, end to end

1. **Intake** — let the user describe the person; slot what they say into the 5
   layers; ask targeted follow-ups only for layers left thin.
2. **Fill blanks by inference** — extrapolate along the grain of their narration;
   mark every layer narrated vs inferred.
3. **Preview** — show the persona back, flag what you inferred, let them correct.
4. **Write** — validate and save to `personas/<id>.json`; point them at `/say-it`.

## Intake — one pass per layer

Don't interrogate. People describe someone in a rush of detail; let them talk and
catch what they say into the layers below, then ask only for what's still thin.
Lead with identity and let it flow toward the relationship — that order feels like
describing a person, not filling a form.

| Layer | What you're after | Ask something like |
|---|---|---|
| **L1 identity** | who they are, role, relation to the user | "Who is this person to you?" |
| **L2 voice** | tone, verbal tics, what they call the user | "How do they talk? Any phrase that's *so them*? What do they call you?" |
| **L3 emotional_triggers** | what sets them off; what of the user's they poke | "What sets them off? What do they needle in you?" (pairs of trigger → reaction) |
| **L4 relationship_dynamics** | the conflict pattern, the typical fight, what the user actually wanted, the **ambivalence** | "How does it usually go wrong between you? What did you want from them that you never got?" |
| **L0 hard_rules** | the negative-space line (see below) | "What would this person *never* say or do, even at their worst?" |

L4 is the say-it-specific layer — it replaces a generic bio with the relationship
itself. `what_user_wants` is the session's destination, so dig for it: not "an
apology" by default but the specific thing (to be seen, to be let go, to be
believed).

## The negative-space question → L0

Always ask: **"What would this person never say or do, even at their worst?"** Those
"out of character" lines become L0 hard rules. The point is not politeness — it's
that the bot must not break character into a *sudden fake apology or comfort* mid-
session. A boss who never says sorry suddenly saying sorry shatters immersion and,
worse, hands the user a fake resolution. L0 nails the persona to who they actually
are. (It also carries the always-on floors: no escalation to verbal abuse, no
attacking the user.)

If the user draws a blank, **reverse-infer L0 from their narration**: given the
person they just described, what is plainly off-limits for that character? Offer it
back as a guess to confirm ("so they'd never *grovel*, right?"), don't impose it.

## Use the conflict vocabulary as a translator

When the user hands you a vague label — "he's just dismissive", "she's cold" — open
`references/conflict-vocabulary.md` and translate that tag into the concrete acting
rules it maps to, then slot those into L2/L3/L4. It turns "dismissive" into
behaviour the bot can actually perform ("cuts you off, looks elsewhere mid-reply,
deflects with 'so?'") so the persona doesn't flatten into a generic bad boss.

Two guardrails on the table:
- It's a **translator, not a classification jail.** The user's own words rank first;
  the table only unpacks a vague label or fills a grain they left unspoken.
- **Tags combine.** One person can be dismissive + credit-stealing + ambivalent at
  once — merge the matched rules, don't force a single category.

Read the file when you actually hit a vague label; you don't need it when the user
is already specific.

## Filling blanks: along the grain, never by stereotype

Some layers will be thin. Fill them by **extrapolating along the grain of what the
user said** — internal consistency with the person they described. Never reach for
demographic, zodiac, or MBTI stereotypes. This is "the person as I perceive them",
not "the average member of their job"; a stereotype fill makes the user say "that's
not *my* boss" and the immersion is gone.

Record what came from where in the `provenance` block: each layer is `narrated`,
`inferred`, or `mixed`. This is not bookkeeping for its own sake — it drives the
preview, where the user gets to correct exactly the parts you guessed.

## The ambivalence field (L4) — preserve the contradiction

L4 requires an `ambivalence` string, and it must hold the contradiction in the
**person's own behaviour** — "usually cold and dismissive, then occasionally checks
in out of nowhere". Do **not** smooth it into something coherent. That unresolved
contradiction is the engine of rumination (the user can neither hate them cleanly
nor let them go), which is precisely why the session needs it. A persona with the
contradiction sanded off can't reproduce the knot the user is stuck on.

Keep it distinct from the **user's own** emotional ambivalence ("I hate him but I
feel guilty") — that belongs in the relationship context (what they wanted, the
fight), not in this field. This field is about *the person's behaviour*.

## Preview before you write

Show the persona back as a readable summary, then:

- Mark each layer **narrated** vs **inferred** (from `provenance`) so the user sees
  what's theirs and what you guessed.
- Invite correction specifically on the inferred parts ("I filled these in — fix
  anything that's off").
- Restate the "this is the person as you perceive them, not the real person" frame.
- Get an explicit confirm before saving.

Corrections at this stage just edit the draft. (The post-session correction *log*,
the `corrections` array, is issue 08 — start it empty here.)

## Write the persona

Build the persona as JSON conforming to
`../say-it/references/schemas/persona.schema.json`. `scripts/sayit_state.py`'s
`persona_template()` is a minimal valid example of the exact shape — match it.
Key fields:

- `schema_version`: `1`
- `id`: a stable slug, lowercase ascii, `relationship-name`, matching
  `^[a-z0-9]+(-[a-z0-9]+)*$` — e.g. `boss-kim`, `mom`, `ex-jun`. If the person's
  name isn't latin, derive a short ascii tag for the slug and keep their real
  name/language in `display_name`.
- `display_name`, `relationship`: the user's own words (may be non-English — this
  is runtime data, stored as-is).
- `layers.L0_hard_rules`: non-empty array of strings.
- `layers.L3_emotional_triggers`: array of `{trigger, reaction}` objects.
- `layers.L4_relationship_dynamics.ambivalence`: **required**, non-empty.
- `provenance`: per-layer `narrated` / `inferred` / `mixed`.
- `corrections`: `[]`.

Then write it to a temp file and save it through the validator (this is the only
sanctioned write path — it validates once at the boundary so a broken persona can't
reach the runner):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/save_persona.py" --file /tmp/persona-draft.json
```

If it exits non-zero it prints the structural errors — fix the JSON and re-run. On
success it reports the saved path. Then tell the user the persona is ready and they
can begin with `/say-it`.

## Multiple personas

Each person is their own file in `personas/`; building a second persona never
touches the first. Before writing, you can check existing ids — if the new `id`
collides with one already there, you'd overwrite it, so confirm with the user
(same person, intentional rebuild?) or pick a more specific slug.

## Language

All of *your* scaffolding — questions, the framing, file/field names — follows the
plugin's English-source rule. The user's narration is captured verbatim into the
persona layers in their own language and stored as data (`ensure_ascii=False`), so
the bot can later perform that voice at runtime. Never hardcode sample dialogue in
a specific language here; the voice comes from each persona's own L2 at session
time.
