# Critique — <subject> <!-- page/component, viewports reviewed, build or file ref -->

Reviewer: <name> · Date: <yyyy-mm-dd> · Stage: <wireframe | comp | build>
Conformance gate: `audit_design.py` <clean | N findings> · review-checklist <run | not run>

> Fill this in, then transcribe to `findings.json` and run
> `python -m scripts.critique_report findings.json` for the ranked version,
> `--format triage` for the tracker, `--format defence` before the meeting.
> Delete every angle-bracket placeholder. A placeholder left in is a finding about you.

---

## What this is trying to do

<One sentence: the page's job and who is on it. If you need an "and also", say so — that
is already a premise finding.>

## What works

<Two or three specific things, named at the mechanism level. "The card rhythm holds at
390px because section spacing is fluid" — not "looks great". This is information: these
are the parts not to touch while fixing everything else.>

---

## Fix these three first

| # | Finding | Severity | Layer |
|---|---|---|---|
| 1 | <title> | <blocking/major/minor> | <layer> |
| 2 | | | |
| 3 | | | |

---

## Findings

<Repeat the block below per finding. Order: severity first, then run-order layer. Stop
writing prose findings after about six — the rest belong in the triage list.>

### <n>. <Title — the observation, not the fix>

`<SEVERITY> · <layer>` · confidence: `<confirmed | likely | suspected>`

**Mechanism.** <What is physically true → what that makes the eye or the user do. This is
the whole finding. If you cannot write this sentence, downgrade to `suspected` and say
what you tried.>

**Evidence.** <file:line, a measurement, a screenshot ref, or the test that showed it.
"Measured 2.98:1" beats "looks light".>

**Fix.** <At the system level: a token, a role, a component API, a base style. If the fix
is local, you have not found the cause yet.>

**Before/after.** <The minimal change that would remove the symptom. If it would not
visibly fix what you described, the mechanism is wrong.>

*Ref: <review-checklist x.y | failure-catalog Lx-y | spacing-system §n>*

---

## Taste, not defect

<Preferences, labelled. Phrase each as a choice with a named alternative, not as an error.
Separated so that disagreeing with them costs the findings above nothing.>

- **<title>** — <why you would choose differently, and what it would buy>

---

## What I am unsure about

<Suspicions with no mechanism yet, and assumptions you made about constraints. Naming
these is worth more than a confident wrong call — and it invites the one person who knows
the constraint to answer.>

- <observation> — tried: <moves from critique-method §2>. Still unexplained.
- Assumed: <constraint you guessed at, e.g. "badge copy is fixed">

## The question I need answered

<The one thing that would change the review. Ask it directly.>

---

## Triage — everything else

<One line each, no prose. Paste from `critique_report.py --format triage`.>

- [ ] `[SEVERITY]` `[layer]` <title> — <fix in one clause>

---

## Conformance

| Gate | Result |
|---|---|
| `python -m scripts.audit_design <path>` | <clean / N errors, M warnings> |
| review-checklist groups 1–12 | <run / partial — say which groups> |
| Contrast measured (not eyeballed) | <yes: contrast.md or a11y_runtime / no> |
| Tabbed with no mouse | <yes/no> |
| 320 / 390 / 768 / 1440 checked | <yes/no> |
| Dark mode toggled and looked at | <yes / proxy: 1440-dark.png, 390-dark.png / no> |
| `prefers-reduced-motion` emulated | <yes / proxy: the reduced-motion captures / no> |

<A "no" on any row is itself a finding — it means the critique below that line is
opinion, not observation.>

---

## Checks a person runs

<`node scripts/critique_snapshots.mjs <url> --out shots` renders a stand-in for each but the
last. Write what was done: a proxy is said as a proxy ("390.png at 390px", never "tested
on a phone"). "Not run — needs a human" is an honest state; a tick for a check nobody
ran is a finding about you.>

| Check | State | What it showed |
|---|---|---|
| Five seconds with someone else | <run: who / proxy: 1440.png, 390.png / not run — needs a human> | <what they said it was for> |
| Squint, blur and 25% | <run / proxy: 1440-blur.png, 1440-25.png / not run — needs a human> | <the two strongest blocks> |
| Flip it | <run / proxy: 1440-mirror.png / not run — needs a human> | |
| Greyscale | <run / proxy: 1440-greyscale.png / not run — needs a human> | |
| On an actual phone | <run: which device / proxy: 390.png / not run — needs a human> | |
| Leave it overnight | <run / not run — needs a human> | |

---

## Presentation defence

<Fill before any meeting. One row, one sentence you say out loud. If it needs a hedge,
the decision is not made yet. Generates from the `decisions` array via `--format defence`.>

| Decision | Why | What you rejected | What it costs |
|---|---|---|---|
| <decision> | <reason> | <alternative and why not> | <the honest downside> |

**Known flaws I am carrying in:** <name them here, before the reviewer does. A flaw you
raise is a judgement call; the same flaw raised by them is an oversight.>

---

## findings.json

```json
{
  "subject": "<subject>",
  "reviewer": "<name>",
  "date": "<yyyy-mm-dd>",
  "decisions": [
    {"decision": "", "rationale": "", "alternative": "", "cost": ""}
  ],
  "findings": [
    {
      "id": "<slug>",
      "layer": "premise|first-impression|hierarchy|structure|craft|color|states|interaction|conformance|presentation",
      "severity": "blocking|major|minor|taste",
      "title": "",
      "mechanism": "",
      "evidence": "",
      "fix": "",
      "confidence": "confirmed|likely|suspected",
      "is_taste": false,
      "status": "open|fixed",
      "defend": false,
      "covers": [],
      "ref": ""
    }
  ]
}
```

`status` — every `open` major or minor finding goes on the defence sheet's "Known flaws"
list, confirmed ones included; mark a finding `fixed` once it is. `defend: true` keeps a
fixed finding on the sheet anyway (to say "we caught and fixed this"). `covers` lists the
audit rules this finding owns when you pass `--audit` (e.g. `["important"]`); only a rule
named there, or written in backticks, is folded into your finding.
