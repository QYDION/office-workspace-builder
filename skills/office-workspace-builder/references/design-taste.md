# Design Taste

## Why this section exists

The most common way a workspace fails is by **looking identical to every other one**. Change the primary colour and a hundred workspaces are still the same skeleton: content sliced into equal-width cards stacked vertically, one border-radius for everything, one shadow on every card. The user can't articulate what's wrong, only that it "looks like a template" — and then they stop using it.

What follows are concrete mechanisms for differentiation, not vague advice about "making it look nice".

---

## 1 · Six tells of a templated workspace

Each one comes with a **detection method** and a **fix**. Check against all six after generating; if you match two or more, redo the visual layer.

### Tell 1 · Uniform border-radius

**Symptom**: cards, list items, buttons, inputs and tags all share one `border-radius`. Visually, everything is "equally important" — there is no hierarchy.

**Detection**: count the distinct `border-radius` values in the CSS, excluding pills (`999px`) and circles (`50%`). **Two tiers or fewer means you've matched this tell.**

**Fix**: radius must **step down by tier** — largest on containers, middle on list items, smallest on controls.

```css
/* Wrong: one value for everything, so everything looks equally important */
.card, .task, .chip, input { border-radius: 14px; }

/* Right: three tiers stepping down, hierarchy is immediately readable */
:root { --radius-lg: 16px; --radius-md: 10px; --radius-sm: 6px; }
.card  { border-radius: var(--radius-lg); }   /* container */
.task  { border-radius: var(--radius-md); }   /* list item */
.chip,
input  { border-radius: var(--radius-sm); }   /* control */
```

### Tell 2 · Uniform shadow

**Symptom**: one `--shadow` is defined and applied to every card. The result reads as "a stack of paper all the same thickness" — zero depth information.

**Detection**: count the distinct `box-shadow` values. **A single value applied to two or more selectors means you've matched this tell.**

**Fix**: **flat cards get no shadow, only a border.** Shadow is a scarce resource, reserved for things that genuinely float above the page — the sticky top bar, the pinned region, overlays. Two tiers at most across the whole thing.

```css
/* Wrong: if every card floats, none of them float */
.card, .overview { box-shadow: 0 1px 3px rgba(16,24,40,.06); }

/* Right: flat areas use borders; shadow signals elevation */
.card { border: 1px solid var(--line); }                 /* flat: no shadow */
.topbar, .today { box-shadow: var(--shadow-float); }      /* raised: sticky bar + pinned region */
```

### Tell 3 · Card conveyor belt

**Symptom**: below the top bar sits a queue of cards, all the same width, height and spacing, one rhythm start to finish. The user can't find the thing they most need to look at.

**Fix**: **there has to be one "bleed" region** — borderless, full-bleed, more generous whitespace, a noticeably larger heading — carrying the most important information. That slot is fixed: **"Today"**. It is the workspace's core value proposition, so it also has to be the visual lead. It must not look like the other cards.

### Tell 4 · Headings with no hierarchy

**Symptom**: every second-level heading uses the same size and weight, distinguished only by shade. Users skimming can't pick out the structure.

**Detection**: count the distinct `font-size` values across `h2` / card headings. **One value means you've matched this tell.**

**Fix**: a size ladder and a weight ladder, with the pinned region clearly larger than ordinary sections.

```css
/* avoid */ .card-head h2 { font-size: 15px; font-weight: 500; }
/* prefer */ .today .card-head h2 { font-size: 17px; font-weight: 500; }
         .card-head h2       { font-size: 15px; font-weight: 500; }
         .slot-hint          { font-size: 13px; font-weight: 400; }
```

### Tell 5 · Palette abuse

**Symptom**: every module gets its own accent colour and the page turns into confetti. Colour is being used as decoration.

**Fix**: **one primary plus one semantic set.** Semantic colours express state, nothing else.

| Purpose | Allowed |
|---|---|
| `--primary` | The only accent: primary buttons, selected state, progress |
| `--danger` (red) | Overdue, delete, error |
| `--ok` (green) | Completed, healthy |
| `--warn` (amber) | Due soon, warning |

**Anything beyond this set means colour is decoration.** Separate modules with headings and whitespace, not colour.

### Tell 6 · Decorative numbering

**Symptom**: `01 / 02 / 03` indices, or a letter-spaced uppercase eyebrow label above every heading. When the content isn't actually a sequence, this is noise added to the page.

**Fix**: **number things only when they truly are a sequence** (steps, a timeline, a ranking). Otherwise drop it.

---

## 2 · Three layout presets

A workspace isn't aiming to be "unique" — it's aiming to **fit its use case**. Three presets cover the large majority of office scenarios. Pick one via `CONFIG.preset` and the tokens apply themselves.

| Token | `calm` | `dense` | `report` |
|---|---|---|---|
| **`--radius-lg`** container | 16px | 10px | 6px |
| **`--radius-md`** list item | 10px | 6px | 4px |
| **`--radius-sm`** control | 6px | 4px | 2px |
| **`--shadow-card`** flat card | none | none | none |
| **`--shadow-float`** raised layer | `0 4px 14px rgba(16,24,40,.08)` | `0 2px 8px rgba(16,24,40,.06)` | `0 1px 3px rgba(16,24,40,.05)` |
| **`--pad-card`** card padding | 20px | 14px | 12px |
| **`--gap`** spacing between cards | 16px | 10px | 8px |
| **`--row-h`** row height | 52px | 40px | 34px |
| **`--fs-body`** body size | 15px | 14px | 13px |
| **`--lh`** line-height | 1.65 | 1.50 | 1.42 |
| **`--today-fs`** pinned heading | 18px | 16px | 15px |
| Separation | whitespace | hairlines | hairlines + header tint |
| Numerals | system | system | monospace `ui-monospace` |
| Feel | roomy, document-like | a full overview per screen | data-dense, print-friendly |

**Hard constraints shared by all three** (these don't vary with the preset):
- Flat cards **never** carry a shadow — a 1px border only
- Radius **always** steps down (lg > md > sm)
- Semantic colours are **used for state only**
- "Today" is **always** a bleed region, and always carries the highest visual weight

### Preset decision table

| Signal | Choose | Why |
|---|---|---|
| Mostly managing your own work, under 50 items, jotting things down on a phone | `calm` | Generous whitespace, large tap targets, uncluttered |
| Many items / several parallel projects / want the whole picture on one screen | `dense` | Trades density for information |
| Reporting, retrospectives, KPIs, metric-heavy; the audience includes a manager | `report` | Aligned numerals, printable, easy to screenshot into a report |
| Phone is the primary device | Take the chosen preset and subtract 2px from `--pad-card` and `--gap` | Whitespace is wasted on a small screen |

**Combining rules**: manager in the audience **and** data-heavy → `report`; phone-first **and** many items → `dense`; otherwise → `calm`.

---

## 3 · Colour discipline

This doesn't vary by preset — all three share one palette structure.

```css
:root {
  --primary: #2563eb;      /* the only accent. Alternatives: teal #0d9488 / indigo #4f46e5 / slate #334155 */
  --primary-soft: #eff6ff; /* a very light wash of the primary, for selected states and tags */
  --danger: #dc2626;  --danger-soft: #fef2f2;   /* overdue / delete / error */
  --ok:     #16a34a;  --ok-soft:     #f0fdf4;   /* completed / healthy */
  --warn:   #d97706;  --warn-soft:   #fffbeb;   /* due soon / warning */
  /* Neutrals: three text levels + two border levels + one background = six */
  --text:#1f2937; --text-2:#6b7280; --text-3:#9ca3af;
  --line:#e5e7eb; --line-2:#f1f3f6; --bg:#f5f7fa;
}
```

**Regional convention (China)**: expense and cost read red, income and growth read green — the opposite of US/European convention. Note that **cost-type metrics invert**: a rising cost is bad news, so it goes red.

---

## 4 · Five pre-delivery questions

Answer these yourself before running any script. **If you can't answer one, the visual layer isn't finished.**

1. **Swap `--primary` from blue to green — is this still the same skeleton?** If only the colour changed, the template feel is unresolved.
2. **How many `box-shadow` tiers are there, and where does each sit?** More than two, or sitting on flat cards, means going back.
3. **How many `border-radius` tiers, and do they step down?** Two or fewer means going back.
4. **Is there a "bleed" region carrying the most important information?** If not, the "Today" block isn't doing its job.
5. **How many colours are on the page?** More than "one primary + three semantic" means colour is being used as decoration.

Questions 1 and 2 are enforced automatically by `scripts/smoke_check.py` (see the `rule 11 design` checks), but **machines can only catch the crudest forms of homogeneity**. Questions 3–5 require human judgement.
