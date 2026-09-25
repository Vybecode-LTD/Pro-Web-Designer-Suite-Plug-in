# Manual Protocol

The two thirds a machine cannot reach, as a timed procedure someone will actually run.

This is written for a developer or designer who is not an accessibility specialist and has not done this before. It is deliberately a script rather than a checklist, because a checklist gets ticked and a script gets *performed* — and the difference is that performing it produces surprise, which is the point.

**Budget: 60–90 minutes per template the first time, 30–45 once the team knows it.** That is the honest cost. It is also less than the cost of one remediation sprint, and vastly less than the cost of a complaint.

## Contents

1. [Before you start](#1-before-you-start)
2. [Keyboard-only walkthrough — 20 minutes](#2-keyboard-only-walkthrough--20-minutes)
3. [Screen reader smoke test — 30 minutes](#3-screen-reader-smoke-test--30-minutes)
4. [Zoom, images off, styles off — 15 minutes](#4-zoom-images-off-styles-off--15-minutes)
5. [The cognitive-load pass — 10 minutes](#5-the-cognitive-load-pass--10-minutes)
6. [Writing a finding so it gets fixed](#6-writing-a-finding-so-it-gets-fixed)
7. [The evidence trail: VPAT, ACR and the client report](#7-the-evidence-trail-vpat-acr-and-the-client-report)
8. [Testing with actual disabled users](#8-testing-with-actual-disabled-users)

---

## 1. Before you start

**Run the automated layers first and fix what they find.** Not because the scanner is more important — it is not — but because thirty minutes of manual attention spent rediscovering a missing `alt` is thirty minutes not spent on the things only you can find. The gate clears the floor.

Then, in order:

| Prepare | Why |
|---|---|
| **Pick one template, not "the site"** | "Audit the site" produces nothing. "Audit the checkout" produces findings by lunchtime |
| **Write down the three things a user comes here to do** | Every test below is one of those tasks attempted. A page has no accessibility properties in the abstract; a *task* either completes or does not |
| **Unplug the mouse.** Physically | Reaching for it is automatic, and every time you reach you stop testing |
| **Open a notes file with columns: what I did, what happened, what I expected** | You will find four things in the first ten minutes and forget two of them |
| **Turn the automated report face down** | You are looking for what it missed. Reading it first tells you where to look, which is the opposite of what you want |

One framing that makes the whole hour better: **you are not inspecting a page, you are trying to get something done.** Buy the thing. Cancel the subscription. Find the phone number. If you catch yourself scanning for violations, pick the task back up.

---

## 2. Keyboard-only walkthrough — 20 minutes

The highest-yield twenty minutes in accessibility testing. No tools, no training, and it finds the class of bug that most reliably makes a site unusable.

### The sequence

**Tab from the very top of the page** — click the address bar, then Tab into the document.

| Step | Do | Notice specifically |
|---|---|---|
| 1 | Tab once | Is the **skip link** the first stop? Does it become **visible** when focused? Activate it — did focus actually land in `<main>`, or did the page just scroll while focus stayed behind? (The second is what happens without `tabindex="-1"` on the target) |
| 2 | Tab through the whole page | **Can you always see where you are?** Not "is there a ring somewhere" — can you find it without hunting. Watch particularly on filled buttons, on dark sections and over images |
| 3 | Keep tabbing, slowly | Does the ring ever **disappear under a sticky header or a cookie bar**? (2.4.11) Scroll-jump is the tell: the page scrolls and the focused thing is behind the header. This is the single most-missed new 2.2 criterion |
| 4 | Watch the order | Read the sequence aloud as a sentence. Does it match what you see, and does it **make sense**? A payment form that goes card → newsletter → CVC has no violations and is wrong |
| 5 | Operate every widget | Dialogs, menus, tabs, accordions, comboboxes, sliders, carousels. Use the keys from `accessibility.md` §4 — the ones you already use everywhere else |
| 6 | Open and close every overlay | Does **Esc** work? Does focus **return to the thing that opened it**? Open a dialog, close it, press Tab: if you land at the top of the page, focus fell to `<body>` |
| 7 | Tab into and out of **every third-party embed** | Maps, video players, payment iframes, chat widgets. This is where traps actually live. Go in, and get out — in both directions |
| 8 | **Shift+Tab all the way back** | Backwards order is where broken focus management hides because nobody tests it. Do the whole page |
| 9 | Submit every form with errors | Where did focus go? To an error summary, or the first invalid field? Or nowhere, leaving you to hunt for red text you may not be able to see |
| 10 | Try to do the three tasks from §1 | Start to finish, keyboard only, no peeking |

### Things people miss on their first pass

- **A hover-only menu.** It opens on hover and has no keyboard path at all. Tab straight past it and you never see the failure — you have to notice the menu *exists*.
- **A control that works but never shows a ring.** You activated it, so you assume it was focused. Go back and look.
- **A ring you can see because you know where it is.** Ask someone else to Tab five times and point at the focused element.
- **`Space` on a `<div role="button">`.** It scrolls the page instead of activating, because `role` adds no behaviour. Try Space *and* Enter on every custom control.
- **A modal you can tab out of behind.** Open it, Tab twenty times, watch whether focus goes into the page underneath. The ring disappearing behind a scrim is the tell.
- **The second dialog.** Esc should close the innermost dismissible thing, one layer at a time. Two layers closing at once is a bug you only find with two layers open.

**If step 2 or step 10 fails, stop and fix it before continuing.** A page you cannot operate with a keyboard has no meaningful screen-reader result, because screen reader users are keyboard users first.

---

## 3. Screen reader smoke test — 30 minutes

You do not need to be fluent. You need to run one honest pass and listen for specific failures.

### Which reader, and the thing nobody tells you

| Platform | Pairing | Notes |
|---|---|---|
| **Windows** | **NVDA + Firefox** | Free. The reference pairing for most developer testing, and closest to what a large share of users run |
| **Windows** | **JAWS + Chrome** | Commercial, and still the most-used reader in enterprise and government. Has its own heuristics that differ materially from NVDA's |
| **macOS** | **VoiceOver + Safari** | Built in (`Cmd+F5`). The only sensible pairing on macOS — VoiceOver with Chrome behaves differently and worse |
| **Android** | **TalkBack + Chrome** | Built in. The realistic mobile test |
| **iOS** | **VoiceOver + Safari** | Built in. Gesture-driven, and a genuinely different interaction model |

**The honest note: these are not proxies for each other.** NVDA+Firefox, JAWS+Chrome and VoiceOver+Safari disagree in ways that change results — how much of an `aria-describedby` is read and when, whether a `role="status"` interrupts, how a table's headers are announced, whether a `<summary>` is a "button" or a "disclosure triangle", how much of a label a form field repeats. A component verified in one can be silently broken in another.

What to do about it, in order of what you can afford:

1. **Test with one, properly.** One real reader beats none by an enormous margin and finds most of what there is.
2. **Add a second on a different engine** for anything custom — a combobox, a tree, a data grid. Different engine is the operative phrase; two Chromium readers tell you less than you think.
3. **Match your actual audience.** A government or enterprise product that has never been tested in JAWS has not been tested.
4. **Say which you used** in the report. "Verified with NVDA 2026.1 + Firefox 142" is evidence. "Screen reader tested" is not.

### Learn five commands, not fifty

| | NVDA | VoiceOver (macOS) |
|---|---|---|
| Start / stop | `Ctrl+Alt+N` | `Cmd+F5` |
| Read next item | `↓` | `Ctrl+Opt+→` |
| **List headings** | `Insert+F7` | `Ctrl+Opt+U` → Headings |
| **List links / landmarks** | `Insert+F7`, change type | `Ctrl+Opt+U` → ← / → |
| Stop talking | `Ctrl` | `Ctrl` |

That is enough. The three lists are where most of the findings are.

### The five tasks

**Do not "browse around".** Browsing produces the impression that it is fine. Attempt these five, in order, and record where you got stuck:

| # | Task | What it tests |
|---|---|---|
| 1 | **Find out what this page is, without looking at the screen.** Turn the monitor off if you can | `<title>`, the h1, the landmark structure. If you cannot answer in fifteen seconds, the page has no orientation |
| 2 | **Read the heading list and predict the page.** Then look | 2.4.6 and 1.3.1 at once. The outline is the table of contents; if it does not describe the page, heading navigation is useless and that is how most screen reader users navigate |
| 3 | **Complete the primary task** — buy, sign up, book, submit | Everything. This is the test; the other four are diagnostics for when it fails |
| 4 | **Submit the form wrong on purpose**, then fix it | 3.3.1 and 3.3.3. Were you told what was wrong? Were you told *where*? Could you get to it? Did the count update audibly when you fixed one? |
| 5 | **Open the links list and read it on its own** | 2.4.4. Count the "Read more" and "Click here" and bare URL rows. Each one is a row a user has to guess at |

### Listen for these seven

| Sound | Means |
|---|---|
| **"button", "link", "edit text" with no name** | Unlabelled control. 4.1.2. Every one is a dead end |
| **"clickable"** (NVDA) on a `<div>` | A fake control. Somebody built a button out of a `<div>` |
| **A filename read aloud** | A missing `alt`. Note: a *missing* attribute, not an empty one |
| **The wrong name** | `aria-label` overriding visible text. The most dangerous thing on this list, because it is invisible to a scanner and to a sighted reviewer |
| **State that never changes** | Toggle every expandable, selectable and checkable thing. "collapsed" that stays "collapsed" is an `aria-expanded` that never updates |
| **The same thing twice** | Two live regions on one message, or `role="alert"` on something that also has `aria-live`. Users turn off announcements that cry wolf |
| **Silence after an action** | The deadliest failure. Submit, delete, filter, add to cart. If nothing is said, the user does not know it worked and will do it again |

That last one deserves its own line. **Silence is the failure mode that produces duplicate orders**, and it is the one a purely visual review never notices, because on screen the change is obvious.

---

## 4. Zoom, images off, styles off — 15 minutes

Three settings, each of which removes one thing the design was leaning on.

### Zoom — 6 minutes

| Do | Look for | SC |
|---|---|---|
| Browser zoom to **200%** | clipped text, overlapping content, a line that needs horizontal scrolling, a fixed-height button whose label now overflows | 1.4.4 |
| **400% in a 1280×1024 window** (equivalent to a 320px viewport) | two-dimensional scrolling; a sticky header eating half the viewport; a nav that vanished rather than collapsed | 1.4.10 |
| Inject the **text-spacing** CSS: `line-height:1.5; letter-spacing:0.12em; word-spacing:0.16em` on `*`, `margin-block-end:2em` on `p` | anything that clips or overlaps. Fixed-height cards and buttons fail here every time | 1.4.12 |
| On a phone, **pinch-zoom** | whether it is blocked at all | 1.4.4 |

The 400% pass consistently finds more than people expect, because it is the state a low-vision user is actually in for hours a day, and almost nobody designs in it.

### Images off — 4 minutes

Disable images in the browser (DevTools → Network request blocking on `*.{png,jpg,webp,avif,svg}` is the quickest route).

- **Every remaining alt text should read as a sentence in place.** This is the fastest quality check on alt text that exists — better than reading the attributes, because you see them in context and instantly notice the ones that repeat the caption next to them.
- **Icon-only buttons that now show nothing** had no text alternative.
- **CSS background images carrying information** disappear with no trace and no alt. That is 1.1.1, and it is why meaningful images belong in `<img>`.

### Stylesheet off — 5 minutes

Disable CSS entirely.

- **Does the page still read in order?** That is 1.3.2, directly, with no tooling.
- **Is the heading structure visible as structure?** Without CSS, an `<h2 class="type-h4">` looks like an h2, which is what it is.
- **Do form labels sit next to their fields?** If they scatter, the association is visual rather than programmatic.
- **Does content appear that was hidden?** Most of the time this is fine (a mobile menu). Sometimes it is a `display: none` skip link, which can never be focused, or a "visually hidden" block implemented with `font-size: 0`.

---

## 5. The cognitive-load pass — 10 minutes

Not a WCAG 2.2 AA requirement in most of its particulars, and the part users feel most. Ten minutes, reading the page as though you are tired, distracted and in a hurry — which is most people, most of the time, and is also an approximation of a permanent condition for many.

| Ask | Failure signature |
|---|---|
| **Can I tell what this page wants me to do in five seconds?** | Three co-equal primary buttons; a hero that describes the company rather than the offer |
| **Is anything time-limited?** | A session timeout, a "code expires in 60s", a checkout hold. All need to be extendable (2.2.1). Someone using a switch device may need ten times as long as you |
| **Does any instruction depend on position, shape or colour?** | "Click the button below", "the red field", "the round icon" (1.3.3). Grep the copy for *above, below, left, right, the blue one* |
| **Is the error message actionable?** | "Invalid" is not. "Enter a date as YYYY-MM-DD" is (3.3.3) |
| **Am I asked for anything twice?** | 3.3.7. Billing address that could have been copied from shipping; a review step that re-asks instead of showing |
| **Can I paste into every field?** | Especially passwords and OTP. `onpaste="return false"` is a direct 3.3.8 failure and blocks password managers (which is half of what makes authentication accessible) |
| **Is anything moving that I did not ask to move?** | An auto-advancing carousel with no pause is a Level A failure (2.2.2), a vestibular trigger, and measurably ignored by users. The cheapest compliant answer is: do not auto-advance |
| **Is the language plain?** | Read one paragraph aloud. If you run out of breath, it is too long. If you have to re-read a sentence, so will everyone |

---

## 6. Writing a finding so it gets fixed

A finding that does not get fixed was not worth finding. The difference is almost entirely in the write-up.

### The template

```
[Severity] Short statement of the barrier
  Where:     URL + selector, or the component name and state
  Steps:     1. … 2. … 3. …            (so anyone can reproduce it in 30 seconds)
  Expected:  what should happen
  Actual:    what happens
  Impact:    who cannot do what, and what it costs them
  Criterion: SC x.x.x (Level A/AA)
  Fix:       the mechanism, not the symptom
  Evidence:  screenshot / screen recording / measurement
```

### The two fields people skip, and which do all the work

**Impact.** Not "fails 2.4.7". *"A keyboard user cannot see which control is focused anywhere in the checkout, so completing a purchase requires counting Tab presses. Affects everyone using a keyboard, a switch device or voice control — and everyone using a trackpad who has pressed Tab by accident."* Severity arguments end when the sentence names a person and a task.

**Fix, as a mechanism.** Not "add a focus style". *"Delete `outline: none` from `.btn:focus` in `buttons.css:42`. The reset is the bug; adding a ring at higher specificity elsewhere leaves the next person one cascade change away from the same failure. If the default ring is visually wrong, replace it in the same rule: `outline: var(--stroke-focus) solid transparent; outline-offset: var(--stroke-focus); box-shadow: var(--shadow-focus);` — the transparent outline is what survives forced-colors, where box-shadow is discarded."*

This is the same standard the scripts in this skill hold themselves to, and it exists for one reason: **a fix applied to a mechanism that was not operating does not work, and nobody can tell whether it helped.**

### Severity, in a scale people accept

| | Meaning | Example |
|---|---|---|
| **Blocker** | A task cannot be completed at all by some group | Keyboard trap in checkout; submit button unreachable |
| **Serious** | The task is completable with significant extra effort or guesswork | No visible focus indicator; form errors that are not announced |
| **Moderate** | Degraded, worked around, annoying | Vague link text; a heading level skip |
| **Minor** | Polish | A redundant role; a landmark label that repeats the role |

### Three rules that get things fixed

1. **One finding per issue, even when the cause is shared.** "Focus ring missing on 14 components" is one ticket that stalls; fourteen tickets get closed.
2. **Attach evidence.** A twelve-second screen recording of the trap ends the discussion. A measurement — `19.52% of pixels change normally, 0.00% in forced-colors` — ends it faster.
3. **File against the component, not the page.** One fix, every page. And it means the `component-state-matrix` cell id is the best possible location field.

---

## 7. The evidence trail: VPAT, ACR and the client report

A VPAT (the template) produces an ACR (the filled-in report about your product). Procurement asks for it, the European Accessibility Act and EN 301 549 make an accessibility statement something a person can rely on, and both are built from evidence you either collected as you went or must now reconstruct at ten times the cost.

### Collect these as you go

| Artefact | From | Keep |
|---|---|---|
| Automated report per template | `a11y_static.py --json`, `a11y_runtime.mjs --json` | every CI run, pass or fail. It is date-stamped evidence |
| Manual protocol run | this file, completed | date, tester, template, reader + browser + versions |
| Screen-reader session recordings | the §3 pass | at least one per major flow |
| Findings and their resolutions | the tracker | including **rejected** ones and why |
| The exceptions table | third-party components | vendor, component, version, ticket ref, date reported, the alternative path offered |
| Key-map config | `a11y-keymap.json` | it documents which widgets are verified and, by omission, which are not |

### The four conformance values, used honestly

| Value | Use when |
|---|---|
| **Supports** | The criterion is met throughout the evaluated scope |
| **Partially Supports** | Met in most places, with named exceptions. **Name them.** An unqualified "Partially Supports" is worth nothing to a buyer |
| **Does Not Support** | Not met. Writing this honestly is what makes the rest of the document credible |
| **Not Applicable** | No content the criterion governs (no video, no audio) |

**"Not Evaluated" is also a legitimate entry.** It is enormously better than a guess, and a reviewer who finds one guess stops trusting the whole document.

### The remark that survives scrutiny

> *"**Supports.** Verified by automated rule (axe-core 4.13 `color-contrast`) across all 14 templates on 2026-09-10, and by manual sampling of 12 representative components in NVDA 2026.1 + Firefox 142 on the same date. Two components use text over photographic backgrounds; these were evaluated by hand against the highest-luminance region of each image."*

Name the tool, the version, the scope, the date, the method and the exceptions. And never write "compliant" on the strength of an automated run — `automation-coverage.md` §7 has the wording, and the reasons it matters legally as well as professionally.

---

## 8. Testing with actual disabled users

**This is the strongest recommendation in the entire skill, and everything above is a substitute for it.**

Every technique in this file is a developer simulating a user. That is genuinely useful and it is structurally limited in one specific way: **you know what the page is supposed to do.** You cannot un-know it. You navigate a broken menu by remembering where the item was; a real user hits the same menu with no model of it and stops. The finding you write is "the arrow keys don't work"; theirs is "I couldn't find the account settings and I gave up".

### What it costs, honestly

| | Typical |
|---|---|
| **Participants** | 5–8 across different assistive technologies and disabilities. Five finds most of what one session can find |
| **Incentive** | Pay the professional rate for their expertise. £/$100–200 per session is normal and is not a favour |
| **Recruiting** | A specialist panel, a disability organisation, or your own users. 1–3 weeks lead time |
| **Sessions** | 60–90 minutes each, moderated, remote is fine and often better — they use their own configured setup |
| **Total** | Roughly **£/$3,000–8,000** for a round, or a specialist agency at £/$8,000–20,000 for a full audit plus user sessions |

Three things that make a round worth more than its cost:

- **Let them use their own setup.** Their reader, their verbosity settings, their braille display, their switch, their magnification. A stock configuration tests a user who does not exist.
- **Give them tasks, not a tour.** "Order a replacement filter" — then be quiet. The silence is where the findings are.
- **Recruit across disabilities, not just screen reader users.** Low vision, motor, cognitive, deaf and hard of hearing, and people with multiple. Screen reader users are the most-tested group and roughly the smallest.

### When the budget does not allow it

Do not conclude the point is unreachable. In rough order of value per pound:

1. **Hire one disabled consultant for one day** to review the primary flow. A single expert session finds more than a week of internal testing, and it is the cheapest line item on the list above.
2. **Ask your existing users.** Some are already disabled and already working around your bugs. A support-ticket search for *screen reader, keyboard, zoom, magnifier, NVDA, JAWS, VoiceOver, contrast* is free and frequently shocking.
3. **Post a support route and read it.** A named contact for accessibility problems, answered by a person, with findings fed into the tracker. This is required by an accessibility statement anyway.
4. **Use a paid remote-testing panel for one round** of unmoderated tasks. Weaker than moderated sessions and a great deal better than nothing.
5. **Test with a disabled colleague** — only if they volunteer, only inside their working hours, and **paid for their time and expertise like any other consultant**. Do not make someone's disability an unpaid second job, and do not treat one person as representative of everyone.
6. **Do the protocol above properly and on a schedule.** Every template, every release. Discipline compensates for a great deal.

### What it does not buy

A user session is not a conformance audit and does not produce a VPAT. Five people will not encounter all 55 AA criteria. **Run both**: conformance testing tells you whether you meet the standard; user testing tells you whether the standard was enough. They disagree more often than anyone expects, and when they do, **the users are right** — the standard is a floor derived from what is defensible, and they are telling you about the thing itself.
