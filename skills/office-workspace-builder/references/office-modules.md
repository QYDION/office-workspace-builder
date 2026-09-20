# Office Module Catalog

Specs for 20+ office modules plus 6 ready-made bundles. Once modules are chosen, take their field and interaction
specs from this table rather than improvising.

**Counting rule**: the pinned "today" block and the top data-overview cards are **fixed blocks** — every workspace
must have them, and they **do not count against the module quota**. The quota counts only the modules selected from
groups A–F below, and **the ceiling is 4**.

**Complexity labels**: ★ simple (≤80 lines) | ★★ medium (80–200 lines) | ★★★ complex (200+ lines). Prefer ★ and ★★
when generating; at most one ★★★ per round.

---

## A · Task execution

### A1. Task list ★★
- **Role**: the spine of the workspace; nearly every office desk should have it
- **Fields**: `id` / `title` / `priority`(P0|P1|P2) / `due`(YYYY-MM-DD) / `done` / `tag` / `note`
- **Interactions**: quick add (title + priority + due date), tick to complete, filter by P0/P1/P2, sort by due date, inline delete
- **Storage**: `{ tasks: Task[] }`
- **Linkage**: the "today" block reads the same `tasks`; the overview completion rate is computed from it too
- **UI notes**: P0 gets a red left bar, P1 amber, P2 grey; completed items get a strikethrough and reduced opacity; the filter row scrolls horizontally on mobile

### A2. Project progress board ★★★
- **Role**: a board view spreading multiple tasks across stages
- **Fields**: `id` / `title` / `stage`(To do|In progress|In review|Done) / `owner` / `due` / `effort`
- **Interactions**: render one column per stage, tap a card to advance its stage (no drag-and-drop — it's poor on mobile and costs a lot of code), filter by owner
- **Storage**: `{ kanban: Card[] }`
- **UI notes**: stack vertically on mobile, each column carries a count badge; distinguish stages with a colour band

### A3. Milestone tracking ★★
- **Role**: a linear timeline of a project's key checkpoints
- **Fields**: `id` / `name` / `date` / `status`(Not started|In progress|Reached|Slipped)
- **Interactions**: horizontal timeline, current checkpoint highlighted, slipped ones in red, a completion-rate ring
- **Storage**: `{ milestones: Milestone[] }`
- **UI notes**: draw the timeline as inline SVG; switch to vertical on narrow screens

### A4. Focus timer (pomodoro) ★★
- **Role**: a single-task timer that sits alongside task execution
- **Fields**: `id` / `taskId` / `minutes` / `startedAt` / `finished`
- **Interactions**: pick a task → start/pause/abandon → on finish, write a focus record and accumulate today's focus minutes
- **Storage**: `{ focusLogs: FocusLog[] }`
- **Pitfall**: don't accumulate with `setInterval` (background tabs get throttled); compute remaining time from `Date.now()` deltas

---

## B · Reporting output

### B1. Weekly report generator ★★★
- **Role**: turns the week's completed work into copy-pasteable text — the single most-wanted feature for anyone reporting upward
- **Fields**: `id` / `week`(2026-W38) / `done`(string[]) / `doing`(string[]) / `blocked`(string[]) / `next`(string[]) / `generatedAt`
- **Interactions**: pull this week's completed items from the A1 task list → generate a four-part text (done this week / in progress / blocked / next week) → copy to clipboard in one click
- **Storage**: `{ reports: Report[] }`
- **Linkage**: depends heavily on A1; also reads stage changes from A2
- **UI notes**: show the result in a `<pre>` monospace block; the copy button uses `navigator.clipboard.writeText` with a fallback to `document.execCommand('copy')`
- **Pitfall**: don't hard-code week numbers — implement `getWeekKey(date)` against the ISO week rules

### B2. Work log ★
- **Role**: a day-by-day record of what was done; the raw material for later weekly reports and reviews
- **Fields**: `date` / `content` / `tag` / `createdAt`
- **Interactions**: date picker + text entry + reverse-chronological list + keyword search
- **Storage**: `{ logs: Log[] }`

### B3. Achievements list ★
- **Role**: captures results worth putting into a review or promotion case
- **Fields**: `id` / `title` / `impact` (quantified) / `date` / `category`
- **Interactions**: add, group by category, export as Markdown text
- **Storage**: `{ achievements: Achievement[] }`

---

## C · Meeting collaboration

### C1. Meeting notes ★★
- **Role**: structured meeting records
- **Fields**: `id` / `date` / `title` / `attendees`(string[]) / `agenda` / `decisions` / `actions`(Action[]) / `createdAt`
- **Interactions**: a note-entry form, a reverse-chronological list, expand for detail, tag-style attendee input
- **Storage**: `{ meetings: Meeting[] }` with `actions` embedded
- **Linkage**: an `action` can be pushed straight into the A1 task list (a one-click "turn into a task")
- **UI notes**: four fixed sections (agenda / decisions / actions / attendees) so the user fills in blanks instead of free-forming

### C2. Follow-up tracker ★★
- **Role**: the board where action items from a meeting actually land
- **Fields**: `id` / `what` / `who` / `due` / `status`(Not started|In progress|Done|Cancelled) / `source` (which meeting)
- **Interactions**: group by who, filter by status, overdue in red, status transitions
- **Storage**: `{ followups: Followup[] }`
- **Linkage**: overdue items surface in the "today" block

### C3. Contact directory ★
- **Role**: pulls scattered collaborator details into one place
- **Fields**: `id` / `name` / `org` / `role` / `contact` / `note` / `lastContact`
- **Interactions**: search, group by organisation, tap to expand
- **Storage**: `{ contacts: Contact[] }`
- **Privacy**: leave phone numbers and similar fields empty for the user to fill in; sample data uses masked formats like `138****0000`

---

## D · Data insight

### D1. KPI cards ★
- **Role**: enlarges the three numbers that matter most
- **Fields**: `label` / `value` / `trend`(up|down|flat) / `delta`
- **Interactions**: mostly static display, tapping drills down into the relevant module
- **UI notes**: the count badge that drills down **must be clickable** (this gets forgotten often)
- **Colour convention**: in office contexts "up = good" rendered green and "down = bad" red holds **only for performance
  metrics**; **cost/expense metrics invert** (a rise is bad news, so it's red)

### D2. Trend line chart ★★
- **Role**: how a value moves week by week or month by month
- **Fields**: `{ series: [{ label, points: [{ x, y }] }] }`
- **Interactions**: switch the time range (last 7 days / last 30 days)
- **UI notes**: hand-write an inline SVG `<polyline>`; include axes, gridlines, data points and hover tooltips (a
  native `<title>` is the easiest tooltip)
- **Pitfall**: past 8 categories on the X axis the labels overlap → show every other one

### D3. Category breakdown (pie/bar) ★★
- **Role**: see the shape of a distribution — tasks by tag, hours by project
- **Interactions**: tap a legend entry to highlight the matching slice
- **UI notes**: draw a donut with inline SVG `stroke-dasharray`; far simpler than computing arc paths

### D4. Goal progress ring ★
- **Role**: what percentage of this month's target is done
- **Fields**: `name` / `target` / `current` / `unit`
- **UI notes**: use the progress-ring template from rule 3; `stroke-dashoffset = circumference × (1 - progress)`

---

## E · Schedule and time

### E1. Schedule / to-dos by date ★★
- **Role**: what to do today and this week, viewed by date
- **Fields**: reuses A1's `tasks`
- **Interactions**: horizontally scrolling date strip, the selected date shows that day's tasks, scrolling across days
- **Key pitfall**: **never let "render the date strip" and "render the day's list" call each other** — this is where
  rule 9 came from. Both read only `State.selectedDate` and `Store.data`, and `refreshAll()` schedules them.

### E2. Week view planner ★★★
- **Role**: a seven-column overview of how the week's time is allocated
- **Interactions**: switch weeks, tap a cell to add, capacity progress bar
- **UI notes**: on narrow screens switch to a seven-row vertical list

### E3. Deadline countdown ★
- **Role**: days remaining across several deadlines
- **Fields**: `name` / `due` / `category`
- **Interactions**: ascending by days remaining, ≤3 days in amber, overdue in red
- **UI notes**: `diffDays` must be implemented through UTC normalisation

---

## F · General support (cross-cutting; does not consume module quota)

### F1. Quick notes ★
- **Fields**: `id` / `content` / `pinned` / `createdAt`
- **Interactions**: a top input that pushes on Enter, pin, delete

### F2. Links / files shelf ★
- **Fields**: `id` / `title` / `url` / `tag` / `note`
- **UI notes**: `<a target="_blank" rel="noopener noreferrer">`

### F3. Tag filtering ★
- Not a standalone module — it's a cross-cutting filter on the A/B/C group lists

---

## 6 ready-made bundles

When the description is vague, start with the closest bundle and say which one you assumed at hand-over.

| Bundle | Modules | Fits descriptions like |
|---|---|---|
| **Efficiency Desk** (most general) | A1 task list + E1 schedule + B2 work log | "I want to keep on top of my day", "a workspace for work", "efficiency desk" |
| **Reporting Desk** | A1 task list + B1 weekly report + D1 KPI cards | "weekly reports are painful", "I have to report upward", "weekly report desk" |
| **Meeting Desk** | C1 meeting notes + C2 follow-up tracker + E1 schedule | "nowhere to keep meeting notes", "I keep forgetting follow-ups", "meeting desk" |
| **Project Desk** | A2 project board + A3 milestones + B1 weekly report | "I'm running several projects at once", "I need the overall picture", "project desk" |
| **Data Desk** | D1 KPI cards + D2 trend chart + D3 breakdown + A1 task list | "I want the data in one place", "a data dashboard", "data desk" |
| **All-rounder** | A1 task list + C1 meeting notes + B1 weekly report + D1 KPI cards | "a bit of everything", "a general office workspace" |

> A bundle is a **starting point, not a destination**. Modules the user explicitly names outrank bundle defaults; if
> the named modules add up to more than 4, run the scope gate from SKILL.md and present a phased plan.
