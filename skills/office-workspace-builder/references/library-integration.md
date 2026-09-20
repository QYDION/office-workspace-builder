# Host Capability Integration

By default a workspace uses the **host-provided "online store / web publishing" capability** to handle building,
storage and deployment. This file covers capability detection, integration, fallback and conflict handling.

> **Why this is written in terms of a "capability" rather than a product name**: the skill should run on different
> hosts. Concrete product names live in the mapping table below; the body uses capability names. Switching hosts
> then means editing the mapping table only, not the logic.

---

## 0 · Host capability mapping table

| Abstract capability | On the reference host (WorkBuddy) | Typical equivalents elsewhere |
|---|---|---|
| Publish an online page | the `资料库` skill's "online page / md-to-web publish" | any static page hosting |
| Online data table (CRUD) | the `资料库` skill's "data table" | Airtable / Notion DB / a cloud database |
| File storage | the `资料库` skill's "netdisk" | any object storage |
| Show a deliverable to the user | `present_files` | any file output / preview mechanism |

**Probe order**: try the reference host's capability first; if unavailable, look for another equivalent; if there is
none → local mode (single-file HTML + localStorage). **Delivery must be reachable in every case** — never abort a
task because one capability is missing.

---

## 1 · Capability detection

Load the capability by its **registered name** `资料库` (that registered name holds only for the reference host).

| Name | Purpose |
|---|---|
| `资料库` | **the registered name — load with this** |
| `library` | **Note:** English alias, for understanding only |
| `skill-library` | **Note:** plugin-internal id, for understanding only |
| `workbuddy-builtin` | **Note:** the built-in plugin's name, for understanding only |

**Never** pass a plugin id or a plugin name where a skill name is expected. A "skill not found" error caused by a
wrong name counts as the capability being unavailable: tell the user plainly and go to local mode. Don't degrade
silently.

> On another host: replace the table above with that host's online-storage and publishing capability names. Nothing
> else in this file needs to change.

The probe result decides whether you run in **cloud mode** or **local mode**. Both paths must reach delivery.

---

## 2 · **Note:** Source of truth for the API: read it at runtime, never invent it

**The concrete API — function names, parameters, return shapes — is whatever the loaded capability's own docs say.**

- Read the capability's docs before generating, and take the real capability names and call signatures from them
- **Don't assemble API names from memory or guesswork.** A misspelled API makes the page fail silently, which is
  worse than not integrating at all
- If the docs are incomplete for one capability (say, the data table), don't guess parameters — use only the
  capabilities that are clear (say, page publishing), fall back to localStorage for data, and say so honestly at
  hand-over

What follows is an **adapter-layer design pattern**, decoupled from any concrete API: whatever the real API looks
like, wrap it in one `CloudAdapter` and let the rest of the page depend only on that adapter's four methods.

---

## 3 · Adapter layer design (front-end structure)

```javascript
/* ===== online storage adapter =====
   Fill these four methods at generation time from the capability's real docs.
   The rest of the page only calls Adapter.pull / push / status and never touches
   the host API directly. */
const CloudAdapter = {
  enabled: false,          // set true when the host store is available
  status: 'local',         // 'synced' | 'syncing' | 'offline' | 'local'

  async pull() {           // read all data from the table; return an object or null
    if (!this.enabled) return null;
    // TODO: implement against the host data-table API — read every row of workspace_{id}
    //       and assemble a Store.data shape
  },

  async push(payload) {    // write Store.data into the table; return true/false
    if (!this.enabled) return false;
    // TODO: implement against the host data-table API — upsert by primary key
  },

  async health() {         // probe connectivity and set status
    // TODO
  }
};
```

**Why an adapter layer**: the host API is only pinned down at generation time, whereas the page's main structure
(rendering, interaction, backup) is stable. Isolating the uncertainty in a small box means an API detail change
touches those 20 lines and nothing else.

---

## 4 · Data-table design conventions

**Table name**: `workspace_{CONFIG.id}`, e.g. `workspace_efficiency_desk`. One table per workspace — sharing a table
across workspaces invites dirty data.

**Recommended shape: one row per record plus structured fields**

| Field | Type | Meaning |
|---|---|---|
| `id` | text (primary key) | unique record id; generate as `timestamp + random suffix` |
| `module` | text | owning module, e.g. `tasks` / `meetings` / `logs` |
| `payload` | long text (JSON) | the record's full data object |
| `updated_at` | number/time | last-modified timestamp — **conflict merging depends on it** |
| `deleted` | boolean | soft-delete flag, so a concurrent delete can't be overwritten back |

**Why store business fields inside a JSON payload rather than one column per field**: modules get added and removed
over time, and every field change would otherwise force a schema change. Carrying business fields as JSON keeps the
schema stable, so iterations need no table migration at all.

**Fallback**: if the host store supports only simple key/value storage and no structured table, degrade to
"single-row whole-blob storage" — one key holding the JSON of the entire `Store.data`. The cost is that concurrent
edits from multiple devices can overwrite each other, so the hand-over note must warn: "avoid editing from several
devices at once".

---

## 5 · Sync flow

### Startup (pull → merge → render)
```
1. Read localStorage for local data (the offline cache layer)
2. CloudAdapter.health() probes connectivity
   ├─ reachable → status = 'syncing', CloudAdapter.pull()
   │     ├─ success → merge with local data by updated_at → write back to localStorage → renderAll()
   │     └─ failure → status = 'offline', renderAll() from local data, and queue this operation
   └─ unreachable → status = 'offline', renderAll() from local data
```

### Change (land locally instantly, push asynchronously)
```
user action → mutate Store.data → write localStorage immediately → refreshAll()   [local always lands first]
                              └→ CloudAdapter.push() async                                  [a failed push never blocks interaction]
```
**Discipline: local first, cloud second.** Never make the user's action wait on the network.

### Offline queue
```javascript
// key: wb_{id}_queue
// shape: [{ op: 'upsert'|'delete', module, id, payload, updated_at }]
```
Once connectivity returns, replay the queue in ascending `updated_at` order, then clear it.

---

## 6 · Conflict handling

**Principle: the newest timestamp wins, and merging keeps both sides' additions (never a wholesale overwrite).**

```javascript
function mergeData(local, remote) {
  if (!remote) return local;
  const out = {};
  const keys = new Set([...Object.keys(local || {}), ...Object.keys(remote || {})]);
  keys.forEach(k => {
    const l = local && local[k], r = remote && remote[k];
    if (Array.isArray(l) || Array.isArray(r)) {
      const map = new Map();
      [...(l || []), ...(r || [])].forEach(item => {
        if (!item || item.id == null) return;
        const prev = map.get(item.id);
        if (!prev) { map.set(item.id, item); return; }
        const pt = prev.updated_at || 0, it = item.updated_at || 0;
        map.set(item.id, it >= pt ? item : prev);   // same id → newer timestamp wins
      });
      out[k] = [...map.values()].filter(x => !x.deleted);
    } else {
      out[k] = (r && (r.updated_at || 0) > (l && l.updated_at || 0)) ? r : l;
    }
  });
  return out;
}
```
Every record must be stamped with `updated_at` on write, otherwise merging degrades into "later overwrites earlier".

---

## 7 · Sync-state UI

A fixed state indicator in the top-right corner, in four states:

| State | Visual | Label |
|---|---|---|
| `synced` | green dot | Synced |
| `syncing` | blue dot + spin animation | Syncing |
| `offline` | amber dot | Offline mode |
| `local` | grey dot | Local storage |

On narrow screens keep only the dot plus a very short label so it doesn't squeeze the title. The indicator is
clickable → expands to show "last synced at" and a "retry sync" button.

```html
</svg>
<span id="sync-dot" class="dot"></span><span id="sync-text">Local storage</span>
```
> Do the spin with CSS `@keyframes` + `transform: rotate()`; don't pull in an animation library.

---

## 8 · Deployment flow

```
1. Publish the HTML as an online page using the host's "online page" / "md-to-web publish"
2. Take the returned live link
3. **Note:** Open it yourself first and verify: the page renders, sample data is present, the sync indicator behaves,
   and adding a record persists
4. Only hand the link over once that passes
```

**If deployment fails**: never hand over a link that doesn't open. Deliver the local HTML file instead, explain that
"deployment failed for now — here's the file, we can retry later", and state clearly that this is local mode with
data in the browser.

---

## 9 · Data compatibility across iterations

> The full iteration workflow, the `CONFIG.id` red line, the five-step module addition and CSV data in/out are in
> `references/iteration-and-data.md`. This section lists only the compatibility rules from the host-store angle.

- Adding a module → new records with a new `module` value; existing records untouched
- Changing a field → **add only, never remove**. When older records lack the new field, the reader falls back to a
  default (`x.newField ?? defaultValue`)
- Removing a module → keep its data (the user may change their mind); just take it out of the UI
- `CONFIG.id` and `tableName` are **immutable once live** — changing them swaps the data table and the user's data
  becomes unreadable
- Data version: increment `Store.data.meta.version` and keep migration logic in one `migrate(data)` function

```javascript
function migrate(data) {
  if (!data.meta) data.meta = { version: 1 };
  if (data.meta.version < 2) {
    // v1 → v2 migration: fill defaults only — remove no fields, rename no fields
    data.meta.version = 2;
  }
  return data;
}
```

> Because business fields ride inside a JSON payload (section 4), **adding a module needs no schema change** — that
> is what makes schema-free iteration possible.
