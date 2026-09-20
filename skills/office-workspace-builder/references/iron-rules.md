# The 13 Iron Rules (full text)

Source: pitfalls collected from 48 real builds plus local end-to-end verification. These are non-negotiable — every build must satisfy all of them.

---

## Quick reference: the usual mistake → what to do instead

Skim this table before writing code; it's faster than reading the long form. Each row is machine-checkable by the scripts in `scripts/` (rule 13 is a behavioural discipline, kept by hand).

| # | Rule | The usual mistake | What to do instead |
|---|------|---------------------|----------------------|
| 1 | Storage & deployment | Data lives only in memory; keys use generic names like `tasks` | Prefer the host's online store; in local fallback, prefix every key with `wb_{id}_` |
| 2 | Data backup | Export buried in settings; import replaces everything | Export/import on the first screen; import **merges**; clearing needs a second confirmation |
| 3 | Fully inlined, zero external links | `<script src="cdn...">`, `font-family: SomeWeirdFont`, emoji as icons | All inlined; charts hand-written as SVG; icons as `<path>`; system font stack |
| 4 | Mobile support | 12px inputs (iOS zooms the page); 32px-tall buttons | Inputs ≥16px; tap targets ≥44px; `env(safe-area-inset-bottom)` |
| 5 | Today block | Only lists what's due today; yesterday's overdue items vanish | Pinned block listing "overdue / today / within 3 days", overdue in red with a one-click action |
| 6 | Seeded sample data | Blank first screen; all samples in the future so nothing looks urgent | 3–5 items, **at least one overdue**; plus a "clear sample data" button |
| 7 | Scope gate | Writing 7 modules in one go and getting a truncated half-file | Over 4 modules → present a phased plan first; oversized file → skeleton first, then one module per write |
| 8 | Regional conventions | Expenses green, income red; currency as `$` | Expenses red, income green; currency `¥`; priority as P0/P1/P2 |
| 9 | No call cycles | `renderCalendar()` calls `renderTodayList()` and vice versa | One-way DAG; `refreshAll()` schedules everything; render functions never call each other |
| 10 | Smoke check | Shipping straight after writing; not re-running scripts after a change | `python scripts/verify.py <file.html>` — all three gates clean before delivery |
| 11 | Design must not be homogeneous | Every element `border-radius:12px`; every card wearing the same shadow | 3–4 radius tiers stepping down; flat cards border-only, shadows reserved for raised layers |
| 12 | Failures must be visible | `try { localStorage.setItem(...) } catch (e) {}` | Record the reason after catching → render it as a user-visible banner; use `@silent-ok` when truly ignorable |
| 13 | File handling discipline | Deleting "useless" files along the way; overwriting a file the user already had | Delete nothing; list what could go and let the user delete it; get consent before overwriting |

---

## Rule 1 · Storage & deployment: prefer the host's online store, fall back locally

**Cloud mode (the host's online store is available)**
- Build: create the workspace HTML page through that capability
- Store: keep all business data in its data-table capability, online and two-way synced
- Deploy: publish as an online page through its web-publishing capability
- Deliverable: a live link that opens on any device
- If the capability fails at runtime → the page switches to localStorage offline mode, shows a notice at the top, and replays the queue once the connection returns

**Local mode (capability unavailable)**
- Single-file HTML, all CSS/JS inlined, data in localStorage — survives refresh and close
- Every localStorage key prefixed `wb_{workspace_id}_` so it can't collide with other pages on the same origin
- Images: compress to 800px wide on upload, at most 9, stored as base64

---

## Rule 2 · Data backup: mandatory, not optional

**Cloud mode**: data syncs automatically, but keep an "export JSON" button as a local snapshot; show a sync-state indicator in the top-right corner (synced / syncing / offline).

**Local mode**:
- **On the first screen**, provide "export JSON" and "import to restore" — don't bury them in settings
- Import must handle thousands of records; no row limit
- Clearing data requires a second confirmation dialog
- Once the user passes 30 records, show a gentle top-of-page nudge: "30 records now — consider exporting a backup"

```javascript
// export
function exportJSON() {
  const blob = new Blob([JSON.stringify(Store.data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = CONFIG.name + '_' + todayISO() + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

// import (no row limit; goes through FileReader)
function importJSON(file) {
  const r = new FileReader();
  r.onload = function (e) {
    try {
      const obj = JSON.parse(e.target.result);
      if (!obj || typeof obj !== 'object') throw new Error('bad format');
      Store.data = mergeData(Store.data, obj);   // merge, not replace — avoids accidental deletion
      Store.save(); refreshAll();
    } catch (err) { alert('Import failed: not a backup file for this workspace'); }
  };
  r.readAsText(file);
}
```

---

## Rule 3 · Fully inlined, zero external links

- Single-file HTML; all CSS and JS inlined
- **Do not reference any external framework, CDN, font, or chart library**
- Draw charts as **hand-written inline SVG** (progress rings, bars, pies, lines)
- Icons are **inline SVG paths**; **never use emoji as icons**
- Font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **The one exception in cloud mode**: calling the data-table API the host's online store provides (an internal capability, not an external dependency)

> Why: if a generated page references an external JS library and the user saves only the HTML, the library 404s and every feature dies.

**Inline SVG progress ring template**
```html
<svg viewBox="0 0 120 120" width="120" height="120" role="img" aria-label="Completion progress">
  <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" stroke-width="12"/>
  <circle cx="60" cy="60" r="52" fill="none" stroke="#2563eb" stroke-width="12"
          stroke-dasharray="326.7" stroke-dashoffset="98" stroke-linecap="round"
          transform="rotate(-90 60 60)"/>
  <text x="60" y="60" text-anchor="middle" dominant-baseline="central"
        font-size="24" font-weight="700" fill="#1f2937">70%</text>
</svg>
```
> `circumference = 2πr`, `stroke-dashoffset = circumference × (1 - progress)`.

**Inline SVG icon template**
```html
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
</svg>
```

---

## Rule 4 · Mobile support: phones are where this actually gets used

- Narrow screens (<768px) collapse to a single column
- Minimum tap target 44×44px (children's apps ≥50px)
- Input font size no smaller than 16px (otherwise iOS zooms the whole page)
- Tables become card lists on narrow screens, or scroll horizontally
- Numeric inputs use `type="number"` to raise the numeric keypad
- Desktop sidebar navigation → bottom tab bar / hamburger on mobile
- Respect the iPhone bottom safe area: `padding-bottom: env(safe-area-inset-bottom)`

```css
:root { --tap: 44px; }
.btn { min-height: var(--tap); min-width: var(--tap); }
input, select, textarea { font-size: 16px; }
.tabbar { padding-bottom: calc(8px + env(safe-area-inset-bottom)); }
@media (max-width: 767px) { .layout { grid-template-columns: 1fr; } }
```

---

## Rule 5 · Pin "what to handle today" to the top

Put a "today" block at the very top of the page, listing three groups automatically:
1. **Overdue and unfinished** — marked red, each with a "push to tomorrow" button
2. **Due today** — highlighted
3. **Due within 3 days** — shown normally

**Anything left unfinished yesterday rolls into today; it must not silently disappear.** Give every row a one-click action (complete / postpone).

```javascript
function getTodayBuckets() {
  const t = todayISO();
  const open = Store.data.tasks.filter(x => !x.done);
  return {
    overdue: open.filter(x => x.due && diffDays(x.due, t) < 0).sort(byDueAsc),
    today:   open.filter(x => x.due === t),
    soon:    open.filter(x => x.due && diffDays(x.due, t) > 0 && diffDays(x.due, t) <= 3).sort(byDueAsc)
  };
}
```

---

## Rule 6 · Seed sample data

- The first open must show 3–5 sample records, **at least one overdue**, so the user immediately sees the point
- Provide a "clear sample data" button
- **Don't let the first screen be blank** — that is the number one reason users decide a tool is no good

Sample wording must be de-identified: use neutral phrasing like "Q3 department budget draft" or "confirm client contract terms". Never fill in real amounts or real client names.

---

## Rule 7 · Scope gate: estimate before building, phase before overrunning

**① Estimate the scope before starting (mandatory)**
After reading the request, estimate the module count and the likely single-file size, then decide whether you can build directly. Each workspace tops out at **3–4 modules**.

**② Over the module limit → present a phased plan before building**
If the request translates to more than 4 modules, do not build everything at once. First present a phased plan: 3 core modules this round, plus a later-iteration plan (which modules go in which round). Once the user accepts or doesn't object, build only the 3 core modules now. Each iteration adds exactly one module, and never loses existing data.

**③ Oversized single file → skeleton first, then incremental writes**
Write the page skeleton first (HTML structure + base styles + a container per module + the init entry point), then fill in modules across several tool calls. The file must stay runnable after each module lands.

```javascript
// Wrong: trying to write 8 modules at once — the output gets truncated, the closing
//    </script> is lost, the static check then discards the whole script block, and every
//    later JS check silently stops working.
//    (smoke_check.py's "rule 10 file integrity" exists for exactly this: the script/style/
//     body/html tags must all close.)

// Right: step one writes only the skeleton (structure + tokens + empty render functions
//           + the init entry point); run verify.py to confirm it works.
//           Then add exactly one module per tool call, running verify.py after each.
//           And re-run the scripts after any change — never skip it on the assumption
//           "I didn't touch that part".
```

**④ Fold the compliance check into the smoke checklist**: confirm the module count is ≤ 4 as part of the rule 10 checklist, item by item, before delivery.

---

## Rule 8 · Regional conventions

- Financial apps: **expenses red, income green** (the opposite of the US/EU convention)
- Currency is `¥` throughout
- Date format: `YYYY-MM-DD` or `MMM D`
- Priority uses P0/P1/P2 rather than High/Medium/Low

---

## Rule 9 · No call cycles: the call graph must be one-way

> Source: a build where "calendar render" and "day-list render" called each other and blew the stack. Bugs like this are syntactically valid and no static check catches them — the architecture has to prevent them.

**One-way rule (non-negotiable)**
- The function call graph must be a **directed acyclic graph (DAG)**; no two functions may form a two-way cycle
- Layered architecture: `data layer (read/write storage) → compute layer (filter/sort/aggregate) → render layer (update the DOM)`. Only upward calls into lower layers, or one-way calls within a layer
- **Render functions never call each other**

**The right way to update coupled views**
- Provide one **single refresh entry point**, `refreshAll()`, that calls each render function in a fixed order
- User interaction → mutate data → call `refreshAll()` → each render function reads the latest data independently

```javascript
// Right: one refresh entry point
function refreshAll() {
  renderTodaySection();
  renderTaskModule();
  renderStats();
  renderSyncStatus();
}

// event handler → mutate data → single refresh
function onToggleDone(id) {
  const t = findTask(id); if (!t) return;
  t.done = !t.done;
  Store.save();
  refreshAll();
}

// Wrong: render functions calling each other → infinite recursion → stack overflow
function renderTodaySection() { /* ... */ renderTaskModule(); }
function renderTaskModule()   { /* ... */ renderTodaySection(); }
```

**Defensive initialisation**: inside the `DOMContentLoaded` callback, run in a fixed order — load data → initialise state → call `refreshAll()` once. Never have individual render functions trigger other render functions.

---

## Rule 10 · Smoke check after generating

**Checklist (confirm each item; if one fails, fix it)**

1. **No call cycles**: draw the call graph and confirm there is no A→B→A or longer cycle
2. **Init chain intact**: walk from `DOMContentLoaded` and confirm every called function is defined and defined before its call site
3. **DOM elements exist**: every `getElementById` / `querySelector` target really is in the HTML
4. **Empty data doesn't crash**: with localStorage empty, the sample-data path fills correctly; clearing samples doesn't throw
5. **Date boundaries correct**: month rollover (Jan 31 → Feb 1) and year rollover (Dec 31 → Jan 1) both compute correctly
6. **Event binding timing**: every `addEventListener` runs after its DOM element is rendered
7. **Variable scope**: no global name collisions; closure variables inside loops are captured correctly
8. **Module count compliant**: this round has ≤ 4 modules; if the original request exceeded that, a phased plan was presented and only the core modules were built; if the file was oversized, it was written skeleton-first then incrementally, and it is complete and runnable
9. **Design not homogeneous**: at least 3 radius tiers; shadows not sprinkled onto flat cards (see rule 11)
10. **Failures visible**: every `catch` either handles the error or is explicitly marked `@silent-ok` with a note on why it's safe to ignore (see rule 12)

**How to run it (four parts, none optional)**

One command runs the first three (recommended):

```bash
python scripts/verify.py <file.html>
```

It runs "ruler self-test → static → runtime" in sequence and fails as a whole if any part fails. Step by step:

1. **Ruler self-test**: `python scripts/selftest.py`
   First confirm the checker itself can be trusted. Every known-bad sample (CDN dependency, emoji icon, fake radius tiers, silently swallowed exception, call cycle, missing DOM node, truncated file, JS syntax error, too many modules, missing CSV path, missing presets) must be flagged, and the baseline skeleton must produce zero false positives.
   **If the ruler is off, the PASS results from the next two parts are meaningless.**
2. **Static checks**: `python scripts/smoke_check.py <file.html>`
   Machine-checkable items: external dependencies, emoji icons, function call cycles, render-function cross-calls, the single refresh entry point, the init entry point, missing DOM elements, module count, mobile essentials, sample data, backup entry point and second confirmation, localStorage prefix, design homogeneity, layout presets, failure visibility, the CSV entry point, **file integrity (unclosed tags = truncation)**, and inline JS syntax.
3. **Runtime checks**: `node scripts/runtime_smoke.js <file.html>`
   Runs the JS for real against a DOM stub (72 assertions): empty-localStorage init doesn't throw, sample data is 3–5 records and includes an overdue one, the pinned block renders content, `refreshAll()` is idempotent across repeated calls, month/year/leap-year dates are right, add/edit/complete/postpone flows work, rendering still works after clearing, **the layout preset lands on `<html data-preset>`**, **CSV parse-and-import works end to end**, **a full storage quota produces a user-visible banner and self-heals once space returns**, and a second init doesn't re-seed sample data.
4. **Manual read-through (not skippable)**: walk the 10-item checklist above by hand, especially items 1, 7, 9 and 10 — no automated check substitutes for taste and semantics.
5. **File discipline (rule 13, purely manual)**: confirm this task **deleted no files**; anything worth deleting has been compiled into a list for the user; and every existing file that was overwritten had consent first.

All three script parts must be at 0 FAIL before delivery.

> **Note:** `runtime_smoke.js` executes the target file's JS inside its own process (no `require`/`process` in the sandbox, but it is not a security boundary). Only run it on workspaces you generated yourself, never on HTML from an unknown source.
> If `node` isn't available, skip part 3 — but then open the result in a browser once by hand before delivering.

### Date arithmetic must be normalised through UTC (avoids timezone/DST drift)

```javascript
function pad2(n) { return String(n).padStart(2, '0'); }
function toISO(dt) { return dt.getFullYear() + '-' + pad2(dt.getMonth() + 1) + '-' + pad2(dt.getDate()); }
function todayISO() { return toISO(new Date()); }
function addDays(iso, n) {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + n);           // Date rolls over month/year boundaries automatically
  return toISO(dt);
}
function diffDays(a, b) {                  // a - b
  const pa = a.split('-').map(Number), pb = b.split('-').map(Number);
  return Math.round((Date.UTC(pa[0], pa[1] - 1, pa[2]) - Date.UTC(pb[0], pb[1] - 1, pb[2])) / 86400000);
}
```
> **Note:** Don't parse `YYYY-MM-DD` with `new Date(isoString)` and then subtract — engines disagree on UTC versus local parsing, and crossing a timezone boundary shifts the result by a day.

---

## Rule 11 · Design must not be homogeneous

> Source: verification found the skeleton had exactly one `box-shadow` value and a single `border-radius: 12px` everywhere — the classic "obviously templated" fingerprint. Everything works, yet it reads as cheap at a glance.
> Full methodology and self-check questions are in `references/design-taste.md`.

**Three hard requirements**

1. **Radius must step down by tier**: container > row > control, at least 3 tiers, decreasing each step.
   Express it with tokens: `--radius-lg: 16px` / `--radius-md: 10px` / `--radius-sm: 6px` / `--radius-xs: 4px`.
   Avoid `border-radius: 12px` on everything
2. **Shadow is a scarce resource**: flat cards get **a border only** (`box-shadow: none`); shadows go only to layers that genuinely float (sticky bar, pinned block, overlays).
   Avoid: every card wearing the same `0 2px 8px rgba(0,0,0,.06)`
3. **The layout must be switchable**: define three presets via `:root[data-preset="..."]` — `calm` / `dense` / `report` — and set the initial value with `<html data-preset="calm">` (otherwise the first frame flashes the default styles).
   - `calm`: generous whitespace, larger type — lifestyle / family apps
   - `dense`: tight line height, information-rich — workplace productivity
   - `report`: small radii, pale colours — dashboards

**Colour discipline**: one primary colour plus a neutral grey scale. Semantic colours (red/yellow/green) are **for state only**, never decoration. Don't spread five colours across the first screen.

**Three questions before delivery**
- Is the radius a single value? → if yes, change it
- Does every card have a shadow? → if yes, cut it back to raised layers only
- Remove the colour and look at greyscale only — can you still tell the hierarchy apart? → if not, the hierarchy is being propped up by colour; redo it

---

## Rule 12 · Failures must be visible: never swallow an exception silently

> Source: verification found the main data write, `localStorage.setItem`, fully swallowed by `catch (e) {}`. When the quota is full or storage is disabled in private mode, the user believes the save went through and loses everything on refresh. Silent data loss is far worse than an error.

**Hard requirements**

1. **A failed main-data write must be visible to the user**: catch it, record the reason, and let the render layer surface it as a banner.
   Avoid: `try { localStorage.setItem(K, d) } catch (e) {}`
   Do record `saveError` → render it inside `refreshAll()` as a banner with a "Got it" button; the message must state the consequence and the way out
2. **The warning must self-heal**: clear `saveError` after the next successful write, or the user stares at a false alarm forever.
3. **A `catch` that is genuinely ignorable must say so explicitly**: write `@silent-ok` plus one line on why it has no side effect; only then will the static check let it pass.
   ```javascript
   // declared-ignorable: failing to write this does not affect the local main flow
   } catch (e) { /* @silent-ok the offline queue is only a push fallback */ }
   ```
4. **A failure the user can act on must include the next step**: not just "it failed", but "click Export to back up now, then remove some old data and retry".

**The correct failure-visibility chain** (note: this still obeys rule 9's one-way calls)

```javascript
// data layer: record the reason only, never touch the DOM
cacheOnly() {
  try { localStorage.setItem(LSK + 'data', JSON.stringify(this.data)); this.saveError = null; return true; }
  catch (e) {
    this.saveError = 'Local save failed: browser storage is full or has been disabled. '
      + 'This change will be lost on refresh — click "Export" to back up now, '
      + 'then remove some old data and try again.';
    return false;
  }
}

// render layer: read saveError and present it — never call back
function renderStorageWarning() {
  const el = document.getElementById('storage-warn');
  if (!el) return;
  if (!Store.saveError) { el.classList.remove('is-on'); el.innerHTML = ''; return; }
  el.classList.add('is-on');
  el.innerHTML = ICON.alert + '<span>' + esc(Store.saveError) + '</span>'
    + '<button class="btn ghost small" data-act="warn-close">Got it</button>';
}

// the single refresh entry point schedules it (rule 9)
function refreshAll() { /* ... */ renderStorageWarning(); /* ... */ }
```

---

## Rule 13 · File handling discipline: delete nothing, ask before overwriting

> Source: a real incident pattern — a build "tidied up" files it had no business touching. In the user's working
> directory, **what looks like a temp file to you may be their only copy**. Deletion is irreversible and costs far
> more than leaving a few extra files around.

### Three hard rules

**① Never delete any file.**
Every file produced during the task stays: intermediate artifacts, old versions, anything that looks duplicated,
anything that looks useless. Delete none of it.
**No exceptions, and not on your own judgement.**

**② What genuinely should go becomes a list the user deletes themselves.**
When the task ends, gather the "suggest deleting" files into a list and hand it to the user. Each entry must include:

| Field | Meaning |
|---|---|
| File path | Full path, so the user can locate it directly |
| Why it's on the list | Temp artifact / old version / duplicate |
| Size | So the user can judge whether it's worth deleting |
| What happens if deleted | State the impact plainly so the user can decide |

Example:
```
The task is complete. These files are worth cleaning up yourself (I deleted nothing):

1. %TEMP%\ows-preopt\          Unpacked pre-optimisation snapshot, only used for this    ~160 KB   No impact if deleted
                               comparison
2. office-workspace-builder.zip  Older package from before the optimisation; contents    ~52 KB   Confirm you no longer need the old
                               are now out of date                                                version before deleting
3. refetch-competitors.py        One-off competitor fetch script from this session        ~3 KB    No impact if deleted
```

**③ Get the user's consent before overwriting an existing file.**
If the target path already holds a file, stop and ask — don't just overwrite:

> "`xxx.html` already exists (12 KB, last modified 3 August). What I'm about to write will overwrite it.
> Is there anything in the original you want to keep? Overwrite / use a different filename / back it up first?"

The explanation must cover **which file would be overwritten, what it currently is, and the blast radius**, so the
user can make an informed decision.

### The one exception

**Delete a file only when the user explicitly names it.** For example, "delete `old.html`" — in that case follow the
instruction, but restate "about to delete: <path>" before you act.

### What this looks like in practice

```javascript
// Wrong: tidying up along the way
fs.unlinkSync('workspace-old.html');        // "it's just an old version" — not your call to make
fs.rmSync('tmp/', { recursive: true });     // "I generated it just now" — it may still be the user's

// Right: delete nothing, produce a list instead
const cleanup = [
  { path: 'workspace-old.html', why: 'superseded', size: '12 KB', impact: 'no impact if deleted' },
  { path: 'tmp/build/',         why: 'build artifact from this run', size: '240 KB', impact: 'no impact if deleted' }
];
reportCleanupList(cleanup);                 // hand it over; let the user decide
```

> **Why so strict**: this skill runs on other people's machines. They lack your context, and deletion is
> irreversible — a few extra files are merely untidy, whereas deleting the wrong one cannot be undone.
