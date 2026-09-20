# Iteration & Data I/O

The first delivery is only the beginning. Reputation is built on the second and third changes — **whether you can
change things without losing the user's data** decides whether they keep using it.

This file covers the two paths that go wrong most often:
- **Iteration**: "add a meeting-notes module", "change the colour", "add a field"
- **Data in/out**: bringing in existing data from Excel / Feishu / Notion, or exporting it

---

## 1 · Iteration: classify first, then act

When an iteration request arrives, work out which class it belongs to — the three carry very different risk.

| Class | Typical phrasing | Risk | Data impact |
|---|---|---|---|
| **Style only** | "change the colour", "smaller font" | Low | None |
| **Adding a module** | "add meeting notes", "I want a dashboard" | Medium | Adds a key; existing keys untouched |
| **Changing fields / structure** | "add an 'estimated effort' field to tasks" | **High** | Needs a migration, or old records lack the field |
| **Changing the workspace id** | "rename it to Project Desk" | **Very high** | See the red line below |

### One red line: don't change `CONFIG.id` once it's live

`CONFIG.id` is the localStorage key prefix (`wb_{id}_`) and half of the host table name. Change it and the storage
bucket changes → **all the user's existing data "disappears"** (it's still under the old key, but to the user it's
gone).

```javascript
// No: the user says "rename it to Project Desk" and the id gets changed along with the name
const CONFIG = { id: 'project_desk', name: 'Project Desk' };   // data all lost!

// Right: change only the display name; leave the id exactly as it was
const CONFIG = { id: 'weekly_report_desk', name: 'Project Desk' };
```

> If the user genuinely wants to start over, remind them to export a backup first and state clearly that the data
> will be cleared.

---

## 2 · Adding a module: five steps, none of which may break existing data

Take "add meeting notes (C1) to the weekly-report desk" as the example.

### Step 1 · Check complexity and quota first

- Current 3 modules + 1 new = **4, exactly at the ceiling** → build directly
- If it became 5 → stop and present a phased plan (see the branch example in `references/worked-example.md`)
- C1 is ★★; the project already has B1 (★★★), so ★★★ still totals 1 → compliant

### Step 2 · Use a new key; don't reuse an old one

```javascript
// Do add a sibling top-level key
Store.data.meetings = [];
// Don't stuff it into tasks: the semantics get muddled, and splitting them later is expensive
```

`ensureShape()` adds only, never removes — that's what lets old backup files keep importing:

```javascript
function ensureShape(d) {
  if (!Array.isArray(d.tasks))    d.tasks = [];
  if (!Array.isArray(d.logs))     d.logs = [];        // new
  if (!Array.isArray(d.meetings)) d.meetings = [];    // new
  // Don't write delete d.xxx — an old backup may hold data the user hasn't migrated yet
  if (!d.meta || typeof d.meta !== 'object') d.meta = { version: 1, updatedAt: Date.now() };
}
```

### Step 3 · Register it in MODULES and refreshAll

```javascript
// MODULES: turn the placeholder slot into a real module (the sidebar and tab bar follow automatically)
{ key: 'meetings', name: 'Meeting notes', icon: 'meet', target: 'module-slot-3' },

// refreshAll: append one line; it's still the only scheduler (rule 9)
function refreshAll() {
  renderNav();
  renderToday();
  renderOverview();
  renderTasks();
  renderLogs();
  renderMeetings();      // new
  renderWeekly();
  renderCsvPanel();
  renderBackupTip();
  renderStorageWarning();
  renderSync();
}
```

Don't call `renderTasks()` from inside `renderMeetings()` — even when they're logically related, mutate the data
in an event handler and then call `refreshAll()` once.

### Step 4 · Migrate (only needed when the field structure changed)

```javascript
function migrate(data) {
  if (!data || typeof data !== 'object') return Store.empty();
  if (!data.meta || typeof data.meta !== 'object') data.meta = { version: 1 };

  // v1 → v2: backfill a default priority on older tasks (missing when the user deleted the field)
  if ((data.meta.version || 1) < 2) {
    (data.tasks || []).forEach(function (t) {
      if (t.priority == null) t.priority = 'P1';       // fill the default; not an error
    });
    data.meta.version = 2;
  }
  return data;
}
```

**Three migration principles**
1. Fill defaults only — remove no fields, rename no fields
2. Increment the version and keep the logic in the single `migrate()` function
3. Run `ensureShape()` once immediately after migrating, as a safety net

### Step 5 · Re-run verification after any change

```bash
python <skill>/scripts/verify.py weekly-desk.html
```

All three gates clean is the definition of done. **In particular, don't skip this on the assumption "I only touched
one module"** — the two things a new module trips over most are "DOM element doesn't exist" and "forgot to register
it in refreshAll, so it never re-renders".

### How the hand-over differs after an iteration

| Mode | Link | Data | What to tell the user |
|---|---|---|---|
| **Cloud mode** | **Link unchanged** | Synced automatically, invisibly | "Meeting notes are in — refresh the page and you'll see them, all your data is still there" |
| **Local mode** | A fresh HTML file to download | Same origin, same key — **still there** | "Just open the new file I gave you. Data lives in the browser and survives as long as you don't switch browsers; to move devices, use Export then Import first" |

---

## 3 · Data in: CSV import

### Why it's mandatory

The strongest data a user has lives in Excel / Feishu bitables / Notion. **With no import path, they have to type
every row by hand** — they give up around row ten and the workspace is dead.

The skeleton already ships the full chain: `parseCSV` / `guessColumn` / `normalizePriority` / `normalizeDate` /
`decodeBytes` / `readCsvFile` / `applyCsvImport` / `renderCsvPanel`.

### The user's flow (three steps; don't add more)

1. Click "Import CSV" in the top bar → a file picker opens
2. The page expands a **column-mapping panel**: auto-guessed mappings plus a 3-row preview
3. Click "Import these N rows" → done, with a note: "N added, M skipped (no title)"

### Technical points (already implemented in the skeleton — don't break them)

| Point | Why |
|---|---|
| **Chinese Excel CSVs are GBK** | Decode strictly with `TextDecoder('utf-8', {fatal:true})` first, fall back to `gbk` on throw — otherwise Chinese text turns to mojibake |
| **A comma inside quotes is not a delimiter** | `"Beijing, Chaoyang",P0` must parse as 2 columns. Support `""` as an escaped quote |
| **BOM and CRLF** | Strip a leading `\uFEFF`, ignore `\r` |
| **Drop blank rows** | Fully blank rows and trailing blank rows must not become empty tasks |
| **Guess column names** | Bilingual hints: `title/task/name/标题/任务/事项`, `priority/level/优先级`, `due/deadline/date/到期/截止` |
| **Normalise priority** | `High/Urgent → P0`, `Medium → P1`, `Low/Normal → P2`, empty → P1 |
| **Normalise dates** | `2026/9/5`, `2026.9.5`, `2026-09-25` all become `YYYY-MM-DD`; `9-25` takes the current year |
| **Reject a missing required column** | If "title" has no mapping, `alert` and stop — **never silently import a pile of empty tasks** |

### Three things the user must be told

1. **`.xlsx` can't be imported** — give the exact route: "if your file is an Excel `.xlsx`, save it as CSV in Excel first"
2. **Import adds, it doesn't replace** — existing data isn't deleted, but importing the same file twice creates duplicates
3. **The mapping is editable** — when the guess is wrong, pick the column from the dropdown

### Data out: three exits, not one

| Exit | Purpose | Where in the skeleton |
|---|---|---|
| **Export JSON** | Complete snapshot, restorable, moves between devices | "Export" in the top bar |
| **Import JSON** | Restore a backup; goes through `mergeData()` to **merge**, not replace | "Import" in the top bar |
| **Import CSV** | Bulk load from Excel / Feishu / Notion | "Import CSV" in the top bar |

> Accounting-style modules add an **export CSV** as well — users want to take it into Excel and compute for
> themselves.
> JSON export/import has **no row limit** (thousands must go through) and uses `FileReader`, not inline strings.

---

## 4 · Checklist for iteration and data operations

After any change, walk this list:

1. `CONFIG.id` untouched (the red line)
2. New data uses a **new key**, not a reused old one
3. `ensureShape()` adds only, never removes — no `delete`
4. If the field structure changed → `migrate()` backfills defaults and the version was incremented
5. The new module is registered in both `MODULES` and `refreshAll()`
6. No new render-to-render calls (rule 9)
7. `python <skill>/scripts/verify.py <file.html>` — all three gates clean
8. Import an **old backup file** once and confirm the old data reads back correctly (a real backward-compatibility test)
9. In cloud mode, open the link yourself and confirm the data is still there and the new module is visible
