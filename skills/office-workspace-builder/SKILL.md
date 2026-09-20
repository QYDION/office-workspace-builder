---
name: office-workspace-builder
description: Generates a ready-to-use office workspace (single-file HTML) from a one-line or paragraph-length natural-language request. By default it deploys through the host's online-storage / web-publishing capability and keeps a data table in two-way sync, returning a live link; if that capability is unavailable it falls back to a local HTML file with localStorage. Use when the user asks for an office workspace, productivity desk, task manager, weekly-report desk, meeting-notes desk, dashboard, schedule, or project board — or asks to turn an office workflow into a working web tool, to make it work well on a phone, or to sync its data across devices.
version: 1.0.0
license: MIT
author: 盘锦奇点科技有限公司 (Panjin QYDION Technology Co., Ltd.)
---

# Office Workspace Builder

Turn a paragraph of office requirements into a workspace the user can open and start using. No ops work, no external dependencies, works on desktop and mobile.

## Input → Output contract

| | Details |
|---|---|
| **Input** | A natural-language request (one sentence or a paragraph). Optionally: workspace name, colour preference, which modules to add or drop |
| **Output** | ① A single-file workspace HTML (fully inlined, works offline) ② By default, a live link after deploying through the host's online-storage capability ③ A short handover note: module list plus suggestions for later iterations |
| **Out of scope** | No accounts, no admin console, no browser push notifications, no large file or video storage, no more than 4 modules per round |

## When to use / when not to

**Use it when**: the user wants an office workflow turned into a web tool; wants a pinned panel saying what to do today; wants a task / reporting / meeting / board / schedule workspace; wants it usable on a phone or shareable with a colleague.

**Don't use it when**:
- The user only wants a document or report file (→ use a document skill)
- The user wants a multi-tenant collaborative SaaS backend (out of scope for a personal workspace)
- The user wants analytical conclusions (→ use a data-analysis capability; no workspace needed)

## Reference files (load as needed — not all at once)

| File | When to read |
|---|---|
| `references/generation-contract.md` | **Always.** Requirement → module mapping, scope-gate algorithm, phased-plan template, generation order, handover wording |
| `references/iron-rules.md` | **Always.** The full 13 rules, the mistake/what-to-do-instead quick-reference table, and code templates. Check against it before generating; run its smoke checklist afterwards |
| `references/design-taste.md` | When choosing colours, radii, shadows, or a layout preset. Six tells that make a page look templated, the `calm` / `dense` / `report` presets, and a pre-delivery taste check |
| `references/worked-example.md` | **On your first build, or whenever you're unsure what a step should look like.** A full walkthrough from S0 to a live link, with the actual code changes, a phased-plan example, and a counter-examples table |
| `references/office-modules.md` | When picking modules. Field/interaction/storage/linkage specs for 20+ modules, plus 6 ready-made bundles |
| `references/library-integration.md` | When deploying through the host's online storage. Capability mapping, data-table design, adapter layer, fallback and conflict handling |
| `references/iteration-and-data.md` | When the user wants to **change an existing workspace** or **bring in Excel/Feishu data**. Iteration red lines (`CONFIG.id` is immutable), the five-step module addition, migration templates, the CSV import path |
| `assets/workspace-skeleton.html` | Copy and adapt this as the base. Ships one fully implemented reference module plus two placeholder slots |
| `scripts/verify.py` | **One command runs all three delivery gates** (recommended entry point): `python scripts/verify.py <generated.html>` |
| `scripts/smoke_check.py` | Static checks: external deps, emoji icons, call cycles, render-function cross-calls, missing DOM nodes, module count, mobile essentials, design homogeneity, layout presets, failure visibility, CSV entry point, file integrity, JS syntax |
| `scripts/runtime_smoke.js` | Runtime checks: executes the JS against a DOM stub — init, sample data, date boundaries, interaction flows, CSV import, storage-full warning, empty-state safety |
| `scripts/selftest.py` | Ruler self-test: confirms the checkers really do flag each known-bad sample. **Run this after touching any checker** — otherwise the PASS results from the other two gates mean nothing |

> **Paths are relative to this skill's root.** The verification scripts inspect structure and behaviour rather than
> wording, so they are not tied to the interface language. Run them from the skill root against whichever
> workspace HTML you generated.

## Standard workflow

### S0 · Probe the host capability (first step of every task)
The workspace deploys through the **host's online-storage / web-publishing capability**. Probe for it using the host mapping table (section 0 of `references/library-integration.md`):

- On the reference host (WorkBuddy) that capability is the `资料库` ("library") skill — load it by its registered name, **`资料库`**. Note the distinction: the registered name is `资料库`; `library` is an English alias and `skill-library` is the plugin-internal id — don't try to load by alias or id.
- On other hosts, use whatever the mapping table lists for online storage and publishing.

- **Probe succeeded** → go "cloud mode": build, store in a data table, deploy, hand over a live link. Tell the user: *"Online storage is available, so your workspace will be deployed — you'll get a link that works on any device, with data syncing automatically."*
- **Probe failed** → go "local mode": single-file HTML plus localStorage. Tell the user: *"Online storage isn't available, so I'll build a local HTML version instead. Data stays in your browser, and there's an export button on the first screen."*

Either way, finish the task. Never abandon it because the capability is missing.

### S1 · Parse the request
Pull out four things. Where something is missing, use the default — **don't open extra clarification rounds for this**:
1. Scenario track (task / reporting / meeting / board / schedule — multiple allowed)
2. Key fields (the concrete objects the user mentioned, e.g. "client name", "contract deadline")
3. Audience (just themselves / themselves + peers / themselves + manager — determines whether reporting export matters)
4. Device emphasis (default both; if they say "mostly on my phone", design mobile-first)

### S2 · Scope gate (hard rule, not skippable)
Estimate how many modules the request translates to:

- **≤ 4** → start building.
- **> 4** → **do not build everything at once.** First present a phased plan: this round covers the 3 core modules, with one more module added in each of rounds 2 and 3, spelling out what each round delivers. Once the user accepts or doesn't object, build only the 3 core modules this round.
- **Single-file output likely to exceed what can be written reliably** (complex modules plus a lot of custom interaction) → write the page skeleton first (structure + styles + a container per module + the `refreshAll()` entry point), then fill in one module per tool call. Keep the file runnable after each module.

The estimation algorithm and phased-plan template are in `references/generation-contract.md`.

### S3 · Generate
1. Copy `assets/workspace-skeleton.html` as the base; change `CONFIG` (workspace name, id, module list), the theme colour, and the page title
2. Fill the selected modules into the placeholder slots per `references/office-modules.md`, following the layered pattern the skeleton demonstrates
3. Remove unused slots and example comments (this means clearing placeholder markers **inside the generated file** — it does not conflict with rule 13's "delete no files"), keeping the section comments readable
4. Seed 3–5 sample items (**at least one overdue**) and provide a "clear sample data" button
5. In cloud mode, wire up data-table reads and writes and show a sync-status indicator

### S4 · Smoke check (required before delivery — run all three gates)

One command does it (recommended):

```bash
python scripts/verify.py <generated.html>
```

It runs "ruler self-test → static → runtime" in sequence and fails as a whole if any step fails. Step by step:

1. **Ruler self-test** `scripts/selftest.py`: confirms the checkers are trustworthy. Every known-bad sample (CDN dependency, emoji icon, fake radius tiers, silently swallowed exception, call cycle, missing DOM node, truncated file, JS syntax error, too many modules, missing CSV path, missing presets) must be flagged, and the baseline skeleton must produce zero false positives. **If the ruler is off, every later PASS is worthless.** Run this whenever you change a checker.
2. **Static** `scripts/smoke_check.py`: catches external links, emoji icons, call cycles, render cross-calls, missing DOM nodes, module count, mobile essentials, design homogeneity, layout presets, failure visibility, the CSV entry point, file integrity, JS syntax.
3. **Runtime** `scripts/runtime_smoke.js`: actually executes the JS against a DOM stub — catches init crashes, date miscalculation, broken interaction chains, CSV parsing errors, and data silently lost when storage is full.

All three must be at 0 FAIL before delivery. Fix and re-run until clean.

Finally, read through the smoke checklist in `references/iron-rules.md` by hand (module count ≤ 4, phasing compliant, no call cycles, design not homogeneous, failures visible). **Automated checks can't replace that manual pass — especially for taste and semantics.**

**Why the runtime gate matters**: a missing function name inside `refreshAll()`, a date off by one day, no null guard after clearing data — static checks see none of these, but the user gets a blank page the moment they open it. This gate holds that line unattended.

> **Note** — `runtime_smoke.js` executes the target file's JS inside its own process (the sandbox has no `require`/`process`, but it is not a security boundary). **Only run it on workspaces you generated yourself**, never on HTML from an unknown source.
> If Node isn't installed, `verify.py` skips the runtime gate automatically — but then open the result in a browser yourself once before delivering.

### S5 · Deploy and hand over (cloud mode)
1. Publish the HTML as an online page using the host capability's web-publishing function
2. Create the data table through its data-table function (name it `workspace_{id}`) and wire up reads/writes
3. Open the link yourself once to confirm it renders, the sample data is there, and the sync indicator behaves
4. Hand over: the live link, the module list, and how to add it to a phone home screen

In local mode: show the user the HTML file (use the host's file-preview capability if it has one), explain that data lives in their browser, remind them to export a backup periodically, and ask whether they want it deployed.

### S6 · Iterate (as needed)
Add one module or change one style at a time. New data fields go under new keys so existing data keeps working; in cloud mode the link stays the same after an iteration.

**Three hard constraints** (details in `references/iteration-and-data.md`):
1. Don't change `CONFIG.id` once it's live — that swaps the storage bucket and the user's existing data becomes unreadable
2. New modules use new keys; `ensureShape()` only adds, never removes — don't write `delete`
3. After any change, re-run `verify.py` and test backward compatibility by importing an **old backup file**

When the user wants to bring in Excel / Feishu / Notion data, use the CSV import path (built into the skeleton) and remind them that `.xlsx` must first be saved as CSV from Excel.

## Pacing the conversation

- Two rounds of confirmation at most, then start. Colours, naming and sample data all have defaults — don't keep asking about them.
- When the request is vague, pick the closest bundle from the "recommended bundles" table in `references/generation-contract.md` and say so at handover: *"I read this as an X-type desk — tell me if that's off and I'll swap modules."*
- Be clear about the deliverable: **a link**, not a pile of code. HTML files don't open inside chat apps, so a link is the only thing that works.
- A deployed page is publicly reachable. Never pre-fill real private data (real amounts, real client names, health data) — sample data always uses neutral wording.

## Don't do these

- Don't pull in any external framework, CDN, font or chart library — draw charts as hand-written inline SVG, use inline SVG paths for icons, **never emoji as icons**
- Don't let the first screen be blank (sample data comes first)
- Don't bury "export backup" in the settings (it belongs on the first screen)
- Don't clear data without a second confirmation
- Don't drop the "today" block — it's the workspace's core value
- Don't pad the feature list past 4–5 modules
- Don't give every element the same border-radius or every card the same shadow — that is the giveaway that makes a page look templated (rule 11)
- Don't write an empty `catch {}` around a storage write — the user will think it saved and lose everything on refresh (rule 12)
- Don't deliver without running the smoke scripts — and re-run them after changes rather than assuming "I didn't touch that part"
- **Don't delete any file** — including intermediate artifacts that look useless. If something really should go, list it (path / reason / size / impact) and let the user delete it themselves (rule 13)
- **Don't overwrite an existing file without consent** — stop first and explain which file you'd overwrite, what's in it now, and what the impact is (rule 13)
