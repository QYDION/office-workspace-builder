# Generation Contract

This is the operating manual for every build: **how to parse the request → how to estimate scope → how to phase
when it overruns → what order to generate in → what to say at hand-over.**

---

## 1 · Requirement parsing: keyword → module

Scan the request for keywords first; each hit becomes a candidate module. Then top up with the default modules for
the scenario track.

### Keyword mapping table

| The user says | Scenario track | Module |
|---|---|---|
| to-do, task, what to do today, priority, P0 | Task | A1 |
| project, progress, board, stage, what's blocking | Project | A2 |
| milestone, checkpoint, key dates | Project | A3 |
| pomodoro, focus, stop getting distracted | Task | A4 |
| weekly report, daily report, status update, reporting upward, summarise the week | Reporting | B1 |
| log, record each day, what I did | Reporting | B2 |
| performance review, promotion, achievements, track record | Reporting | B3 |
| meeting, minutes, attendees, agenda | Meeting | C1 |
| follow-up, action items, who owns it, action | Meeting | C2 |
| client, contact, address book | Meeting | C3 |
| data, dashboard, metric, KPI, report | Data | D1 |
| trend, direction, change, line | Data | D2 |
| share, distribution, pie, breakdown | Data | D3 |
| goal, progress, completion rate, how much done | Data | D4 |
| schedule, calendar, this week, planner | Schedule | E1 |
| shift, week plan, time allocation | Schedule | E2 |
| countdown, deadline, due, how many days left | Schedule | E3 |
| quick note, idea, memo, sticky note | Support | F1 |
| bookmark, link, file, reference | Support | F2 |

### Four things you must extract

1. **Scenario track** (multiple allowed, e.g. "task + reporting")
2. **Key fields**: the concrete objects the user named — "client name", "contract deadline", "project code" — these
   shape the module's field design
3. **Audience**: just themselves / themselves + peers / themselves + a manager. If a manager is involved, reporting
   export (B1 or B3) has to be possible
4. **Device emphasis**: both by default; if they say "mostly on my phone", design mobile-first (the bottom tab bar
   leads, and desktop is just the stretched-out version)

### Fallback for a vague request

When the user says only something like "build me an office workspace":
- Go straight to the **Efficiency Desk** bundle (A1 + E1 + B2) without asking
- At hand-over, explain: "I built the most general setup — task list, schedule and work log. If you'd rather have
  weekly reporting, meeting notes or a data dashboard, say the word and I'll swap modules."

**Don't open extra clarification rounds just to be thorough.** Two at most; the second should already be the build.

---

## 2 · The scope-gate algorithm

### Step 1: count modules
```
candidate modules = de-duplicated keyword hits + bundle top-ups
```
Note: group F (quick notes / link collecting / tag filtering) plus the "today" block and the data overview
**do not count against the quota**.

### Step 2: decide
| Module count | Action |
|---|---|
| 1–2 | On the light side — add one module from the same track to reach 3 (mention it, don't ask) |
| 3–4 | Build directly |
| ≥5 | **Present a phased plan first; building everything at once is not allowed** |

### Step 3: estimate the size (this decides the generation strategy)
```
expected lines ≈ Σ complexity per module (★≈80 / ★★≈160 / ★★★≈260) + skeleton overhead ≈ 500
```
| Expected lines | Generation strategy |
|---|---|
| ≤ 900 | Write the whole HTML in one pass |
| > 900 | **Write the skeleton first (structure + styles + module containers + the refreshAll entry point), then fill in one module per write**, keeping the file runnable after each |

> **Note:** Exceeding the single-write limit truncates the output and produces a half-file that is worthless. Better to
> write in three passes than to gamble on one.

### Step 4: constrain complexity
At most **one ★★★ module per round**. If two ★★★ modules are candidates, push the weaker one to round two.

---

## 3 · Phased-plan template (use directly when there are ≥5 modules)

```markdown
Your request works out to N modules, which is past the 4-module ceiling for a single workspace. Piling on
features makes the page sluggish and more fragile, so I'd suggest two phases and getting the core running first:

**Phase 1 (this delivery) — the 3 core modules**
1. {Module A}: {one line on what it does}
2. {Module B}: {...}
3. {Module C}: {...}

**Phase 2 (added once you confirm) — 1 module**
4. {Module D}: {...}

**Phase 3 (optional)**
5. {Module E}: {...}

Phasing loses no data — phases 2 and 3 add to the same workspace and everything already there stays.
I'll start with the 3 modules from phase 1, sound good? (If I don't hear back I'll go with that.)
```

Key points:
- Say **what each phase delivers**, not just module names
- Say explicitly that **no data is lost** — that's the user's main worry
- Offer a "no reply means go ahead" exit so nothing stalls

---

## 4 · Generation order (follow strictly)

### Pass 1 · Skeleton
Copy `assets/workspace-skeleton.html` and change four things:
1. Edit `CONFIG`: `id` (lowercase English with underscores, e.g. `efficiency_desk`), `name` (the workspace's display
   name), `tableName` (`workspace_{id}`)
2. Edit the theme colour `--primary` and the `<title>`
3. Adjust the `MODULES` array to this build's modules
4. Keep the "today" block and the top data overview (both fixed blocks)

### Pass 2 · Fill in module by module
For each chosen module:
1. Find its placeholder slot inside `<main>` (`<!-- MODULE:n START -->` ... `<!-- MODULE:n END -->`)
2. Replace it with the module's real HTML structure plus render function and event handling
3. Name render functions `render{ModuleName}()` and register them in `refreshAll()` **in the fixed order**
4. Store the module's data under its own key in `Store.data`; never share a key with an existing module

**After each module the file must be runnable** — that's the discipline of incremental writing. If something goes
wrong halfway, any intermediate state is still better than a half-file.

### Pass 3 · Data and samples
1. Add 3–5 sample records covering this build's modules inside `Store.sampleData()`, **at least one overdue**
2. Confirm the "clear sample data" button clears cleanly without throwing

### Pass 4 · Self-check and deploy
1. `python scripts/verify.py <file.html>` → all three gates (ruler self-test / static / runtime) clean
   - To run them separately: `python scripts/selftest.py` → `python scripts/smoke_check.py <file.html>` → `node scripts/runtime_smoke.js <file.html>`
2. Read through the rule 10 smoke checklist by hand (10 items; the ones that matter most are no call cycles, design
   not homogeneous, failures visible)
3. Cloud mode: deploy through the host capability → open the link yourself → hand over

---

## 5 · Naming and colour defaults

Don't ask the user about these — use the defaults and mention at hand-over that they can be changed.

| Item | Default |
|---|---|
| Workspace name | Named after the bundle: "Efficiency Desk", "Weekly Report Desk", "Meeting Desk", "Project Desk", "Data Desk". If the user gave a name, use theirs |
| `CONFIG.id` | Lowercase English with underscores, `^[a-z][a-z0-9_]{2,30}$` |
| Theme colour | `#2563eb` (a steady office blue) |
| Alternatives | Teal `#0d9488`, indigo `#4f46e5`, graphite `#334155` |
| Layout | Top title bar + pinned "today" block + a card flow of modules; ≥768px gets left sidebar navigation |
| Radius / shadow | `--radius:14px`; `0 1px 3px rgba(16,24,40,.06)` |
| Background | `#f5f7fa` page with `#ffffff` cards |

Colour constraint: desktop and mobile share one set of CSS variables, so **never hard-code colours** — changing the
theme means changing `--primary` only.

---

## 6 · Internal prompt skeleton (follow this shape when generating)

```
Single-file HTML, "{workspace name}". {one-line scenario description}.

{the core beyond the 0-1 fixed blocks: today}

N modules:
1. {module name}: {fields} — {core interaction}
2. ...

Put "today" at the very top of the page, overdue items in red with a one-click postpone button, and roll anything
unfinished yesterday into today.
Put three data-overview cards plus one progress ring near the top.

Look: clean white background, rounded cards, primary colour {theme colour}.
Works on phone and desktop: single column on mobile, buttons ≥44px, input font ≥16px, bottom tab bar with safe-area
padding.

Data: the host data table `workspace_{id}` for online storage plus two-way sync; fall back to localStorage when
unavailable (key prefix `wb_{id}_`). The first screen has "export JSON" and "import to restore", and a sync-state
indicator sits in the top-right corner.

All inlined — no external framework/CDN/font/chart library. Charts hand-written as inline SVG, icons as inline SVG.

Seed 3–5 sample records (one overdue) with a "clear samples" button.

Architecture: data layer → compute layer → render layer, one-way calls only. refreshAll() is the single refresh
entry point, and render functions never call each other (that causes recursive stack overflow).
```

---

## 7 · Hand-over wording

### Cloud mode
```markdown
"{workspace name}" is built and live 

**Live link**: {link}
Opens directly on phone or desktop, and data syncs automatically.

**This round's N modules**
1. {Module A} — {one line}
2. {Module B} — {one line}
3. {Module C} — {one line}

Plus two fixed blocks: the "today" block at the top (overdue items flagged red and rolled forward), and the data
overview above it.

**On your phone**: open the link in the browser → Share → Add to Home Screen, and it behaves like an app.

**About the data**: the link is publicly reachable (anyone with it can open it), but the data lives in your own
host storage, and nothing real is pre-filled in the page.
```

### Local mode
```markdown
"{workspace name}" is built (local version)

**File**: {path}
Double-click to open. Data lives in your browser, so refreshing or closing loses nothing.

**This round's N modules**: {same as cloud mode}

**Note:** Two things to know about the local version:
1. Switching browsers or clearing the cache loses the data → "export JSON backup" is on the first screen; save one now and then
2. To use it on your phone or share it with a colleague, it needs to be deployed as a live link — want me to do that?
```

---

## 8 · Anti-patterns (any of these means rework)

| Anti-pattern | Why it doesn't work |
|---|---|
| Cramming 5+ modules into one round | The page gets sluggish and the failure rate jumps; users find it harder to use, not easier |
| Referencing Chart.js / Tailwind / an icon font from a CDN | The user saved only the HTML → the assets 404 → every chart is empty |
| Emoji as icons | Renders inconsistently across devices and looks unprofessional |
| A blank first screen, waiting for the user to enter data | They decide it's no good at first glance |
| Two render functions calling each other | Stack overflow; the page goes blank |
| "Export backup" hidden three levels deep in settings | Not findable = no backup = lost data = your fault |
| Delivering before checking on a real run | A broken link goes out and the experience collapses |
| Pre-filling real client names or amounts | The link is public — that's a leak |
| Dropping the "today" block | The workspace loses its core value and degrades into a plain table |
