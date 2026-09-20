# Full worked example: from one sentence to a live link

This file walks a real request through S0 → S5, **showing the actual code changes at each step**. Copy the structure
when you're unsure; don't invent a new one.

It also includes a "request over the limit → phase it" example and a counter-examples table.

---

## The request

> Writing my weekly report is painful. I want to note down what I do each day, then have Friday's report assemble
> itself in one click. While I'm there I'd like to see how much I finished this week and whether anything is
> slipping.

---

## S0 · Probe the host capability

Probe for the host's online-storage / web-publishing capability using the mapping table.

- Probe succeeded → **cloud mode**. Opening line:
  > "Online storage is available, so your workspace will be deployed — you'll get a link that works on any device,
  > with data syncing automatically."
- Probe failed → **local mode**. Opening line:
  > "Online storage isn't available, so I'll build a local HTML version instead. Data lives in your browser, and
  > there's an export button on the first screen."

This example continues in **cloud mode**.

---

## S1 · Parse the request (extract four things, ask nothing)

| Item | Result here | Evidence |
|---|---|---|
| Scenario track | Reporting (weekly report) | "assemble itself in one click" |
| Key fields | date, content, tag, week | "what I do each day", "weekly" |
| Audience | just themselves (possibly showing results to a manager) | no colleagues mentioned |
| Device emphasis | both (default) | nothing stated |

"How much I finished this week, whether anything is slipping" → carried by the **fixed data-overview cards**
(unfinished / overdue / finished this week plus a progress ring). That **doesn't consume module quota**, so no extra
module is needed.

---

## S2 · Scope gate (count before building)

| Candidate module | Code | Complexity | Decision |
|---|---|---|---|
| Task list | A1 | ★★ | keep — the skeleton ships a reference implementation, and it's the report's data source |
| Work log | B2 | ★ | keep — "note down what I do each day" |
| Weekly report generator | B1 | ★★★ | keep — the core request |
| Trend line chart | D2 | ★★ | drop — the overview cards already cover "how much I finished" |

**3 modules ≤ 4 → build directly**, no phased plan.

> At most one ★★★ per round — here that's only B1, so it's compliant.
> If the user later says "I'd also like meeting notes and a KPI board", that becomes 5 modules → the phased-plan
> example at the end of this file applies.

Complexity labels and field specs are in `references/office-modules.md`.

---

## S3 · Generate (four passes; the file is runnable after each)

### Pass 1 · Skeleton and configuration

Copy `assets/workspace-skeleton.html` and change three things:

```javascript
// ① CONFIG: id must match ^[a-z][a-z0-9_]{2,30}$, and tableName must follow the id
const CONFIG = {
  id: 'weekly_report_desk',
  name: 'Weekly Report Desk',
  tableName: 'workspace_weekly_report_desk',
  preset: 'dense',          // workplace productivity → the dense preset (see design-taste.md)
  maxModules: 4
};

// ② MODULES: drives the sidebar and bottom tab bar. Remove the unused slot3 placeholder
//    from the HTML (note: this means clearing a placeholder marker inside this file —
//     not deleting any file; see rule 13)
const MODULES = [
  { key: 'today',   name: 'Today',       icon: 'cal',   target: 'today-card' },
  { key: 'tasks',   name: 'Tasks',       icon: 'list',  target: 'module-tasks', built: true },
  { key: 'logs',    name: 'Work log',    icon: 'note',  target: 'module-slot-2' },
  { key: 'weekly',  name: 'Weekly report', icon: 'doc', target: 'module-slot-3' }
];

// ③ Page title: change both <title> and <span id="brand-name"> to "Weekly Report Desk"
```

> Also sync `data-preset="dense"` onto the `<html>` tag — otherwise the first frame flashes the `calm` styles.

### Pass 2 · Fill in the modules

**Slot 2 → B2 work log** (simpler structure; do it first so the file stays runnable)

```html
<!-- MODULE:2 START — work log (B2) -->
<section class="card slot" id="module-logs">
  <div class="card-head"><h2>Work log</h2><span class="muted" id="log-count"></span></div>
  <form class="task-form" id="log-form" autocomplete="off">
    <input type="date" id="log-date" aria-label="Date" required>
    <input type="text" id="log-content" placeholder="What you did today, e.g. compared contract clauses" maxlength="120" required>
    <input type="text" id="log-tag" placeholder="Tag" maxlength="12">
    <button class="btn primary" type="submit">Record</button>
  </form>
  <div class="filters" id="log-filters">
    <button class="chip is-on" data-act="log-filter" data-val="all">All</button>
  </div>
  <ul class="log-list" id="log-list"></ul>
</section>
<!-- MODULE:2 END -->
```

Its JS: `Store.data.logs` (a new key, **leaving the existing `tasks` untouched** — so iteration stays backward
compatible), `renderLogs()`, `onAddLog()`, `onDeleteLog()`.

**Slot 3 → B1 weekly report generator** (★★★, do it last)

```html
<!-- MODULE:3 START — weekly report generator (B1) -->
<section class="card slot" id="module-weekly">
  <div class="card-head"><h2>Weekly report</h2><span class="muted" id="weekly-week"></span></div>
  <div class="csv-acts" style="margin-bottom:10px">
    <button class="btn primary" data-act="weekly-gen">Generate this week's report</button>
    <button class="btn ghost" data-act="weekly-copy">Copy</button>
  </div>
  <pre id="weekly-output" class="muted">Click "Generate this week's report" to gather this ISO week from the task list and the work log.</pre>
</section>
<!-- MODULE:3 END -->
```

**Key: register them in the single refresh entry point** (rule 9, fixed order)

```javascript
function refreshAll() {
  renderNav();
  renderToday();
  renderOverview();
  renderTasks();
  renderLogs();        // new
  renderWeekly();      // new
  renderCsvPanel();
  renderBackupTip();
  renderStorageWarning();
  renderSync();
}
```

Don't call `renderWeekly()` from inside `renderLogs()` — that is exactly the rule 9 cycle.

**Week numbers must follow the ISO rules, never hard-coded**:

```javascript
function getWeekKey(d) {
  const dt = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  dt.setUTCDate(dt.getUTCDate() + 4 - (dt.getUTCDay() || 7));   // move to this ISO week's Thursday
  const y0 = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1));
  const wk = Math.ceil(((dt - y0) / 86400000 + 1) / 7);
  return dt.getUTCFullYear() + '-W' + String(wk).padStart(2, '0');
}
```

Show the result in a `<pre>` monospace block with four sections: done this week / in progress / blocked / next week.

### Pass 3 · Data and samples

```javascript
sampleData() {
  const t = todayISO();
  return {
    tasks: [
      { id: 'sp1', title: 'Draft the Q3 department budget',      priority: 'P0', due: addDays(t, -2), done: false, tag: 'Budget',   note: '', updated_at: Date.now() - 90000 },
      { id: 'sp2', title: 'Write up Wednesday product review',    priority: 'P1', due: t,               done: false, tag: 'Meeting',  note: '', updated_at: Date.now() - 80000 },
      { id: 'sp3', title: 'Refresh the project milestone board',  priority: 'P2', due: addDays(t, 2),   done: false, tag: 'Project',  note: '', updated_at: Date.now() - 70000 },
      { id: 'sp4', title: 'Compile last week timesheet report',   priority: 'P2', due: addDays(t, -1),  done: true,  tag: 'Report',   note: '', updated_at: Date.now() - 60000 }
    ],
    logs: [
      { id: 'sl1', date: addDays(t, -1), content: 'Compared contract clauses and produced a difference list', tag: 'Contract', createdAt: Date.now() - 50000 },
      { id: 'sl2', date: t,              content: 'Confirmed the new board information hierarchy with design', tag: 'Collaboration', createdAt: Date.now() - 40000 }
    ],
    meta: { version: 1, updatedAt: Date.now() }
  };
}
```

**At least one item must be overdue** (`sp1` has a `due` two days back with `done: false`); keep the wording
de-identified — no real client names or amounts.

### Pass 4 · Self-check

```bash
python <skill>/scripts/verify.py weekly-desk.html
```

---

## S4 · Self-check output (this is what you should see before delivering)

```
Checker regression tests -- 12 cases

[OK]  Baseline sample (skeleton as shipped)  zero FAIL
[OK]  External CDN dependency                caught as expected
...
Checker regression: 12 passed | 0 failed
Ruler is trustworthy: no false positives on the good sample, every bad sample caught

[OK] FAIL 0  |  WARN 0  |  PASS 25 -- ready to deliver
[OK] FAIL 0  |  PASS 72 -- runtime behaviour is sound

All 3 gates passed -- ready to deliver
```

If any part shows FAIL or WARN, **fix it before delivering** — never ship with a warning outstanding.

---

## S5 · Hand-over wording

> The Weekly Report Desk is built and live: **<live link>**
>
> **3 modules**
> 1. **Tasks** — quick add with P0/P1/P2, tick to complete, sort by due date
> 2. **Work log** — one entry a day, tagged and searchable
> 3. **Weekly report** — gathers this ISO week's tasks and log entries in one click, producing four sections you
>    can paste straight into Slack or email
>
> The "Today" block at the top automatically lists overdue / due-today / due-within-3-days items, flags overdue ones
> in red and lets you push them forward in one click; the overview cards show unfinished, overdue, finished-this-week
> and the completion rate.
>
> **On your phone**: open the link in the browser → Share → Add to Home Screen, and it's an app.
> Data lives in your host storage and syncs across devices; "Export JSON" on the first screen gives you a snapshot
> at any time.
>
> If you want more, a later round can add meeting notes or a KPI board — just say the word.

---

## Branch example · request over the limit → present a phased plan first

> The user changes tack: "I'd also like meeting notes, a KPI board, a project board and a focus timer."

Module count = 4 (existing) + 4 (new) = **8 > 4** → **building it all at once is not allowed**; present a phased
plan:

| Phase | Delivers | Increment notes |
|---|---|---|
| **Phase 1 (this delivery)** | Tasks + work log + weekly report | The 3 already built above; get the spine running |
| **Phase 2** | + meeting notes (C1) | Meeting actions convert into tasks in one click |
| **Phase 3** | + project board (A2) | Vertical stacking on mobile, tap a card to change stage |
| **Phase 4** | + KPI board (D1+D2; focus timer on request) | Drill down from the overview cards into charts |

Once the user confirms, **deliver phase 1 only this round**. Each phase's new module uses a new storage key (such as
`meetings`), and `ensureShape()` only adds fields, never removes — not a single old record is lost.

---

## Counter-examples (what these approaches cost you)

| The wrong approach | Consequence | What to do |
|---|---|---|
| `<script src="https://cdn.jsdelivr.net/npm/chart.js">` | The user saved only the HTML → the library 404s → every chart dies | Hand-write inline SVG `<polyline>` |
| Using a checkmark emoji as an icon | Renders inconsistently across platforms and looks cheap | Inline SVG `<path>` |
| Every element `border-radius: 12px`, every card the same shadow | "Obviously templated"; reads as cheap | 4 radius tiers stepping down; flat cards `box-shadow: none` |
| `catch (e) {}` around `localStorage.setItem` | Silent data loss when storage is full; everything gone after a refresh | Record `saveError` → a visible banner (rule 12) |
| `renderCalendar()` and `renderTodayList()` calling each other | Infinite recursion → blank page | Both only read state; `refreshAll()` schedules them |
| A blank first screen, waiting for the user to add data | They decide it's no good and close it | Seed 3–5 items including one overdue |
| Writing 8 modules in one pass | Truncated output → `</script>` lost → blank page | Skeleton first, then one module per round, running verify.py each time |
| Export buried under "Settings → Advanced → Data" | Nobody finds it; lost data becomes your problem | Put it in the top bar on the first screen |
