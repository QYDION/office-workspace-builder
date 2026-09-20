<a href="https://www.qydion.com" target="_blank" rel="noopener"><img src="https://qydion.com/brand/16-horizontal-full-deepspace.png" alt="QYDION" width="240"></a>

# office-workspace-builder

> [中文](README.md) | English

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![type: Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-blue.svg)](skills/office-workspace-builder/SKILL.md)
[![verify: 3 gates · 0 FAIL](https://img.shields.io/badge/verify-3%20gates%20%C2%B7%200%20FAIL-brightgreen.svg)](#verification)

## Included skill

| Skill | Description |
|---|---|
| `office-workspace-builder` | Turns a one-line office request into a workspace the user can open and start using. It produces a single-file HTML page with all CSS, JS, icons and charts inlined and zero external dependencies; by default it deploys through the host's online-storage capability and hands over a live link, falling back to local HTML plus localStorage when that capability is unavailable. Ships 20+ office modules, 13 hard-won rules, and three automated verification gates that run before delivery. |

## What it fixes

Asking a model to generate a workspace page directly tends to hit the same set of failure modes. This skill turns each one into a rule with an executable check behind it:

| Common problem | How this skill handles it |
|---|---|
| An external JS library is referenced, the user saves only the HTML, the library 404s, everything breaks | Fully inlined; charts drawn as hand-written inline SVG |
| Blank first screen waiting for the user to add data, so the user decides it is useless | Ships 3-5 sample items, one of them already overdue |
| Modules pile up, a single generation gets truncated, blank page | Scope gate: at most 4 modules per round; anything larger gets a phased plan first |
| Render functions call each other, infinite recursion, stack overflow | One-way call graph; `refreshAll()` is the single refresh entry |
| A failed storage write is swallowed by `catch`, the user assumes it saved, data is lost on refresh | Failures must surface as a user-visible warning banner |
| Every element shares one border-radius and every card carries the same shadow, so it reads as a template | Radius steps down by tier; shadows reserved for raised layers |
| Delivered straight after generation, so runtime errors go unnoticed | Three automated verification gates before delivery |

## Installation

**Option 1: skills CLI**

```bash
npx skills add QYDION/office-workspace-builder --skill office-workspace-builder
```

**Option 2: manual**

Download this repository and copy the entire `skills/office-workspace-builder` folder into your client's skills directory (the location differs per client — check that client's documentation), then restart once.

Afterwards just describe what you want in plain language — *"build me a weekly-report desk"*, *"I want to log what I do each day and have it stitched together on Friday"* — with no special commands.

> The skill ships 7 reference documents and 1 skeleton template. **After modifying it, reload the full skill**, so the client does not keep executing only the opening portion it happened to inject.

## Repository layout

```
.
├── LICENSE
├── README.md
├── README.en.md
└── skills/
    └── office-workspace-builder/
        ├── SKILL.md                        Skill entry point (contract, S0-S6 workflow)
        ├── references/                     7 reference documents
        │   ├── iron-rules.md               The 13 rules in full + a mistake/what-to-do-instead table
        │   ├── generation-contract.md       Requirement -> module mapping, scope gate, generation order
        │   ├── office-modules.md           20+ module specs + 6 ready-made bundles
        │   ├── design-taste.md             Colour / radius / shadow discipline + 3 layout presets
        │   ├── library-integration.md       Host capability mapping, fallback, conflict handling
        │   ├── iteration-and-data.md        Iteration red lines, 5-step module addition, CSV import
        │   └── worked-example.md            End-to-end walkthrough + counter-examples
        ├── assets/
        │   └── workspace-skeleton.html     Skeleton template (1,367 lines, passes every check)
        └── scripts/                        Verification scripts
            ├── verify.py                   One-shot entry for all three gates
            ├── selftest.py                 Regression tests for the checkers
            ├── smoke_check.py              Static checks
            └── runtime_smoke.js            Runtime checks
```

## Requirements

| Item | Required? | Notes |
|---|---|---|
| Python 3.8+ | For verification | Standard library only — no pip installs |
| Node.js | Optional | Needed for JS syntax checking and the runtime smoke test; skipped with a notice if absent |
| Host online-storage / publishing capability | Optional | If available the workspace is deployed and synced across devices; otherwise it falls back to local storage |

The generated workspace itself has **zero dependencies** — it runs straight in a browser.

## Verification

One command runs all three gates:

```bash
python skills/office-workspace-builder/scripts/verify.py <generated-workspace.html>
```

| Gate | Script | What it does |
|---|---|---|
| 1 · Ruler self-test | `selftest.py` | Confirms the checkers themselves are trustworthy: every known-bad sample must be caught, and the baseline skeleton must produce zero false positives |
| 2 · Static checks | `smoke_check.py` | External deps, emoji icons, call cycles, render cross-calls, missing DOM nodes, module count, mobile essentials, design homogeneity, layout presets, failure visibility, CSV entry point, file integrity, JS syntax |
| 3 · Runtime checks | `runtime_smoke.js` | Runs the inlined JS against a DOM stub: init, sample data, date boundaries, interaction flows, CSV import, storage-full warning, empty-state safety |

Run them individually if you prefer:

```bash
python skills/office-workspace-builder/scripts/selftest.py                  # ruler self-test
python skills/office-workspace-builder/scripts/smoke_check.py  <file.html>  # static
node   skills/office-workspace-builder/scripts/runtime_smoke.js <file.html> # runtime
```

Current state of the bundled skeleton: **ruler self-test 12/12 · static 25 PASS / 0 FAIL / 0 WARN · runtime 72 PASS / 0 FAIL**.

> **Why the ruler self-test comes first**: a broken checker will happily report PASS on bad code. Every ruler has to be measured against known-bad input — only then does its PASS mean anything.

## The 13 rules

The skill's core is a checklist distilled from real failures. The full version lives in [`references/iron-rules.md`](skills/office-workspace-builder/references/iron-rules.md), each rule paired with a contrast and a code template.

| # | Rule | Gist |
|---|---|---|
| 1 | Storage & deployment | Prefer host online storage; fall back to local; consistent key prefix |
| 2 | Backups | Export/import on the first screen; import merges; clearing needs confirmation |
| 3 | Fully inlined | No CDN, fonts or chart libraries; icons as inline SVG |
| 4 | Mobile fit | Tap targets ≥44px, inputs ≥16px, respect the iPhone safe area |
| 5 | Today block | Pinned block for overdue / today / next 3 days; overdue in red with one-tap postpone |
| 6 | Sample data | 3-5 items including one overdue; never an empty first screen |
| 7 | Scope gate | ≤4 modules per round; larger gets a phased plan; oversized output starts with a skeleton |
| 8 | Regional conventions | Expense red, income green, ¥, P0/P1/P2 priorities |
| 9 | No call cycles | One-way DAG, single `refreshAll()`, render functions never call each other |
| 10 | Smoke check | All three gates green before delivery; re-run after every change |
| 11 | Design discipline | 3-4 radius tiers stepping down; shadows only on raised layers |
| 12 | Failures must be visible | Render caught errors for the user; explicitly declare ignorable ones |
| 13 | File handling | Delete nothing; list cleanup candidates for the user; get consent before overwriting |

## Compatibility

The skill is designed around **abstract capability <- mapping table -> concrete host**, so it is not tied to any single platform:

| Abstract capability | Reference host | Other hosts |
|---|---|---|
| Publish a web page | the built-in library skill | any static hosting |
| Online data table | the built-in data-table capability | Airtable / Notion DB / cloud DB |
| Present deliverables | `present_files` | any file-preview mechanism |

Switching hosts means editing the mapping table only (section 0 of `references/library-integration.md`); the skill logic is unchanged.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE) © 2026 盘锦奇点科技有限公司 (Panjin QYDION Technology Co., Ltd.)
