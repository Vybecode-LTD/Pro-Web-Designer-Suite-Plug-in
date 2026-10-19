# Self-Review Protocol — 20 minutes

Run this before a client meeting, a design review, or a PR that anyone senior will read.

It is timed because self-critique without a clock either finds nothing (you look at what
you meant) or finds everything (you spiral at 1am). The clock forces breadth first, depth
second — which is also the order that matches how a reviewer's attention moves.

**Set a timer for each step and move on when it fires, even mid-thought.** An unfinished
observation written down is worth more than a finished one you did not reach.

## Before you start (2 min, does not count)

- Open the brief in a second window. You will read it again at minute 18.
- Open `assets/CRITIQUE_TEMPLATE.md` or a blank findings file. Write every observation the
  moment you have it; do not fix anything until the timer is done. **Fixing is the enemy
  of finding** — one fix costs ten minutes and ends the pass.
- Run the machine gate now so it finishes while you work:
  ```bash
  python -m scripts.audit_design <path> --json > audit.json
  ```
- Have ready: a contrast picker, the responsive bar at 390 and 1440, and a phone.

---

## The routine

| # | Time | Step | What you are looking for |
|---|---|---|---|
| 1 | 0:00–2:00 | **Premise, from the brief** | Read the brief, then write in one sentence what the page is for. Compare to what it does |
| 2 | 2:00–3:00 | **Five seconds, then away** | Look, close the laptop, write what you remember and what you think it is for |
| 3 | 3:00–4:00 | **Squint and shrink** | Blur to ~8px, then view at 25%. Name the two strongest blocks. Is the primary action one of them? |
| 4 | 4:00–5:00 | **Flip it** | Mirror the page (DevTools `transform: scaleX(-1)` on `<body>`). Imbalance and alignment errors jump out of a mirrored image |
| 5 | 5:00–6:00 | **Greyscale it** | `filter: grayscale(1)`. Whatever hierarchy survives is real; whatever collapses was being propped up by color |
| 6 | 6:00–9:00 | **Trace and interrogate** | Trace your first three fixations. Then walk the page saying each gap's meaning out loud — the sentence that will not finish is the finding |
| 7 | 9:00–11:00 | **Measure the three you assumed** | Heading-to-body size ratio, two gaps you believe are equal, and muted text contrast. Numbers, not impressions |
| 8 | 11:00–13:00 | **Phone** | Open it on an actual phone. Section padding, tap targets, the hero's real content, and how many scrolls to the first useful thing |
| 9 | 13:00–15:00 | **States** | Tab the whole page with no mouse. Then force empty, loading and error. Then the longest plausible string |
| 10 | 15:00–16:00 | **Dark mode and motion** | Toggle the theme and look at every surface; emulate `prefers-reduced-motion: reduce` |
| 11 | 16:00–18:00 | **Fold in the machine gate** | `python -m scripts.critique_report findings.json --audit audit.json` |
| 12 | 18:00–20:00 | **Re-read the brief, then rank** | Anything in the design answering no question the brief asked? Then rank and cut to three |

---

## What each step defeats

| Step | The blindness it removes |
|---|---|
| Brief first | Scope drift — you have been looking at the design, not the problem, for days |
| Five seconds | Your belief about what the page communicates. You have never seen it fresh |
| Squint / shrink | Detail obsession. Only structure survives, which is what a reviewer sees first |
| Flip | Composition blindness. A mirrored layout is a new image to your visual system |
| Greyscale | Color propping up a hierarchy with no structural basis |
| Gaps out loud | Values chosen by eye. A guessed value has no sentence |
| Measure | The two things you are sure are equal. They are the near-miss findings |
| Phone | Desktop-only generosity, and what the hero actually says at 390px |
| States | Everything designed against the happy path |
| Brief again, last | The beautiful thing you added that answers nothing |

---

## Output

```bash
python -m scripts.critique_report findings.json --audit audit.json --summary
python -m scripts.critique_report findings.json --audit audit.json --format defence
```

Three things to fix, and the sheet you take into the room. Nothing else gets acted on in
the time you have.

---

## Rules

1. **Write, do not fix.** One fix mid-pass costs the remaining fifteen minutes.
2. **Finding nothing means the steps were skipped**, not that the work is clean. Every
   layer produces either a finding or an explicit "checked, clean" — and "clean" requires
   naming what you checked.
3. **Rank before you act.** The rubric is indifferent to how you feel at 1am:
   does it break → does it mislead → does it cheapen → is it just my preference.
4. **Label your taste before anyone else does.** An unlabelled preference discovered by a
   reviewer makes every other decision look accidental.
5. **If step 1 produces a finding, stop and fix that.** A premise failure makes the other
   eleven steps a critique of the wrong page.

## When you have longer

| You have | Add |
|---|---|
| +1 night | Sleep on it and re-run steps 2–5. Sleep is the only reliable familiarity solvent |
| +5 min | Show it to one person for five seconds and ask what it was for. Their answer is the finding |
| +15 min | Read the page backwards, last section to first, so no block borrows momentum from the one before it |
| +30 min | Full `review-checklist.md`, all twelve groups |

Method behind every move: `references/critique-method.md` §2 and §6.
