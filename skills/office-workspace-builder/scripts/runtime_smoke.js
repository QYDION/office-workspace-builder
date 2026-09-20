#!/usr/bin/env node
/**
 * runtime_smoke.js — runtime smoke test for office workspaces (office-workspace-builder)
 *
 * smoke_check.py handles the static half (external deps / call cycles / DOM presence / module count).
 * This script covers the dynamic half: it actually runs the workspace's inline JS against a minimal DOM stub to verify
 *   1. initialising with an empty localStorage does not throw and seeds sample data correctly
 *   2. the sample-data count is legal and at least 1 item is overdue (rule 6)
 *   3. the today block really renders content (rule 5)
 *   4. refreshAll() can be called repeatedly and stays idempotent (rule 9: the refresh entry must be stable)
 *   5. date maths is correct across months / years / leap years (rule 10, item 5)
 *   6. interaction flows (add / edit / delete / toggle done) work end to end and persist
 *   7. the page still renders after clearing data (empty state does not crash; rule 10, item 4)
 *   8. init writes CONFIG.preset onto <html data-preset> (rule 11: the preset mechanism really takes effect)
 *   9. CSV parsing: commas inside quotes / escaped double quotes / BOM / CRLF / blank lines / empty string
 *  10. CSV import end to end: column guessing + priority and date normalisation + persistence + rejecting a missing required column with a prompt
 *  11. rule 12: when storage is full, saveError is recorded, the banner is visible, and it self-heals on recovery
 *  12. a second initialisation is idempotent: no duplicated sample data
 *
 * [!] The DOM stub returns an element for any getElementById, so this script does NOT verify that DOM elements exist;
 *    that is smoke_check.py's DOM check. The two scripts are meant to be used together.
 *
 * Usage:
 *   node runtime_smoke.js <workspace.html>
 * Exit code: 0 = everything passed; 1 = an assertion failed or init threw
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// ------------------------------------------------------------------ result collection
const results = [];
function pass(name, detail) { results.push({ ok: true, name, detail: detail || '' }); }
function fail(name, detail) { results.push({ ok: false, name, detail: detail || '' }); }
function assert(cond, name, detail) { cond ? pass(name, detail) : fail(name, detail); }
function assertEq(actual, expected, name) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  a === e ? pass(name, a) : fail(name, 'expected ' + e + ', got ' + a);
}
/* Used by the UI-text checks: one assertion set covers workspaces in any language.
   The English patterns use a word-boundary lookahead so a CSS class such as is-overdue cannot satisfy the overdue-group assertion. */
function hasAny(text, patterns) {
  const s = String(text == null ? '' : text);
  return patterns.some(function (p) { return p.test(s); });
}

// ------------------------------------------------------------------ DOM stub
function makeEl(id) {
  const el = {
    id: id || '',
    innerHTML: '',
    textContent: '',
    value: '',
    title: '',
    className: '',
    hidden: false,
    files: null,
    style: {},
    dataset: {},
    children: [],
    _attrs: {},
    _listeners: {},
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
      toggle(c, force) {
        if (force === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); }
        else if (force) { this._s.add(c); } else { this._s.delete(c); }
      }
    },
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener() {},
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { return c; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
    focus() {},
    click() {},
    getAttribute(k) { return this._attrs[k] !== undefined ? this._attrs[k] : null; },
    setAttribute(k, v) { this._attrs[k] = String(v); },
    scrollIntoView() {},
    insertAdjacentHTML() {},
    getBoundingClientRect() { return { width: 0, height: 0, top: 0, left: 0 }; }
  };
  return el;
}
function fire(el, type, ev) {
  const l = (el && el._listeners && el._listeners[type]) || [];
  let out;
  l.forEach(function (fn) { out = fn(ev || {}); });
  return out;
}

// ------------------------------------------------------------------ main flow
async function main() {
  const file = process.argv[2];
  if (!file) { console.log('Usage: node runtime_smoke.js <workspace.html>'); process.exit(2); }
  if (!fs.existsSync(file)) { console.error('File not found: ' + file); process.exit(1); }

  const html = fs.readFileSync(file, 'utf8');
  const blocks = [];
  const re = /<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) blocks.push(m[1]);
  const js = blocks.join('\n;\n');

  console.log('\n━━━ ' + path.basename(file) + ' | runtime smoke ' + '━'.repeat(30));
  if (!js.trim()) { console.error('no inline <script> found'); process.exit(1); }

  // ---- build the sandbox
  const els = new Map();
  const lsMap = new Map();
  const alerts = [];
  const confirms = [];
  /* Storage-full switch: once true, every localStorage.setItem throws QuotaExceededError,
     which is how the failures-must-be-visible rule is verified (rule 12). */
  const lsState = { fail: false };
  const lsStub = {
    getItem(k) { return lsMap.has(k) ? lsMap.get(k) : null; },
    setItem(k, v) {
      if (lsState.fail) {
        const err = new Error('The quota has been exceeded.');
        err.name = 'QuotaExceededError';
        throw err;
      }
      lsMap.set(k, String(v));
    },
    removeItem(k) { lsMap.delete(k); },
    clear() { lsMap.clear(); }
  };

  const documentStub = {
    title: '',
    body: makeEl('body'),
    documentElement: makeEl('html'),
    _listeners: {},
    getElementById(id) {
      if (!els.has(id)) els.set(id, makeEl(id));
      return els.get(id);
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    createElement(tag) { return makeEl(tag); },
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener() {}
  };

  /* Getter for lazily created DOM elements  --  calling E() directly returns undefined */
  const E = function (id) { return documentStub.getElementById(id); };

  const sandbox = {
    document: documentStub,
    localStorage: lsStub,
    console: { log() {}, warn() {}, error() {}, info() {} },
    setTimeout, clearTimeout, setInterval, clearInterval,
    Blob: function (parts) { this.parts = parts; },
    URL: { createObjectURL() { return 'blob:stub'; }, revokeObjectURL() {} },
    FileReader: function () { this.readAsText = function () {}; },
    alert(msg) { alerts.push(String(msg)); },
    confirm(msg) { confirms.push(String(msg)); return true; },
    navigator: { clipboard: { writeText() { return Promise.resolve(); } } },
    /* Needed by the CSV decode path: decodeBytes() probes UTF-8 / GBK with TextDecoder + Uint8Array */
    TextDecoder, TextEncoder, Uint8Array, Uint16Array, ArrayBuffer,
    Math, Date, JSON, Object, Array, String, Number, Boolean, Map, Set, Promise, RegExp, Error, isNaN, parseInt, parseFloat
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  const ctx = vm.createContext(sandbox);

  // ---- expose internal bindings for the assertions
  // const/let declarations do not land on the sandbox, so they have to be exported explicitly; 
  // each name is probed individually so a missing one is reported by name, rather than a single CONFIG is not defined hiding the real problem.
  const EXPORT_NAMES = ['CONFIG', 'Store', 'State', 'CloudAdapter', 'MODULES',
    'refreshAll', 'addDays', 'diffDays', 'todayISO', 'uid', 'esc', 'fmtDate',
    'getStats', 'getBuckets', 'onToggle', 'onAddTask', 'onDelete', 'onPostpone',
    'onFilter', 'clearAll', 'exportJSON', 'init',
    'parseCSV', 'guessColumn', 'normalizePriority', 'normalizeDate', 'decodeBytes',
    'applyCsvImport', 'renderCsvPanel', 'CSV_FIELDS', 'renderStorageWarning'];
  const exportLine = '\n;globalThis.__X__ = (function(){'
    + ' var out = {}, names = ' + JSON.stringify(EXPORT_NAMES) + ';'
    + ' for (var i = 0; i < names.length; i++) { try { out[names[i]] = eval(names[i]); } catch (e) {} }'
    + ' return out; })();';

  let initThrew = null;
  try {
    vm.runInContext(js + exportLine, ctx, { filename: 'workspace.js' });
  } catch (e) {
    initThrew = e;
  }
  if (initThrew) {
    fail('script executes without throwing', String(initThrew && (initThrew.stack || initThrew.message)));
    report(1);
    return;
  }
  pass('script executes without throwing', 'inline JS parses and runs inside the sandbox');

  const X = sandbox.__X__ || {};
  const REQUIRED = ['Store', 'refreshAll', 'todayISO', 'addDays', 'diffDays'];
  const missing = REQUIRED.filter(function (k) { return !X[k]; });
  if (missing.length) {
    fail('skeleton structure complete', 'missing required internal exports:' + missing.join(', ')
      + '(this file may not be derived from workspace-skeleton.html -- check by hand)');
    const known = EXPORT_NAMES.filter(function (k) { return X[k]; });
    if (known.length) console.log('  [INFO] exports actually reachable:' + known.join(', '));
    report(1);
    return;
  }

  // ---- init: simulate a first open (empty localStorage)
  const domReady = documentStub._listeners['DOMContentLoaded'] || [];
  assertEq(domReady.length >= 1, true, 'registers a DOMContentLoaded init entry point');

  let initErr = null;
  try {
    for (const fn of domReady) await fn({});
  } catch (e) {
    initErr = e;
  }
  if (initErr) {
    fail('initialising with no data on first open does not throw', String(initErr && (initErr.stack || initErr.message)));
  } else {
    pass('initialising with no data on first open does not throw', 'init() completes normally');
  }

  // ---- sample data (rule 6)
  const tasks0 = X.Store.tasks();
  assert(tasks0.length >= 3 && tasks0.length <= 5, '3-5 sample items', 'actual ' + tasks0.length + ' items');
  const t0 = X.todayISO();
  const overdue0 = tasks0.filter(function (x) { return !x.done && x.due && X.diffDays(x.due, t0) < 0; });
  assert(overdue0.length >= 1, 'sample data contains at least 1 overdue item', overdue0.length + ' overdue');

  const keys = Array.from(lsMap.keys());
  assert(keys.length > 0 && keys.every(function (k) { return k.indexOf('wb_') === 0; }),
    'every localStorage key carries the wb_ prefix', keys.join(', ') || '(no writes)');

  // ---- layout presets (rule 11): init must write CONFIG.preset onto <html data-preset>,
  //      otherwise the whole token set is inert in a different scenario and the preset mechanism is pointless
  const presetAttr = documentStub.documentElement.getAttribute('data-preset');
  const wantPreset = (X.CONFIG && X.CONFIG.preset) || 'calm';
  assertEq(presetAttr, wantPreset, 'init writes the layout preset onto <html data-preset>');

  // ---- today block rendering (rule 5)
  const todayHtml = E('today-body') ? E('today-body').innerHTML : '';
  assert(todayHtml.length > 40, 'the pinned block renders output', todayHtml.length + ' chars');
  assert(hasAny(todayHtml, [/已逾期/, /(^|[^-\w])overdue/i]),
    'the pinned block marks the overdue group', '');
  const taskListHtml = E('task-list') ? E('task-list').innerHTML : '';
  assert(taskListHtml.indexOf('task-title') >= 0, 'the task list renders items', taskListHtml.length + ' chars');

  // ---- refreshAll idempotence (rule 9)
  let repeatErr = null;
  try { for (let i = 0; i < 5; i++) X.refreshAll(); } catch (e) { repeatErr = e; }
  assert(!repeatErr, 'calling refreshAll() 5 times in a row does not throw', repeatErr ? String(repeatErr) : '');

  // ---- date boundaries (rule 10, item 5)
  assertEq(X.addDays('2026-01-31', 1), '2026-02-01', 'month rollover: Jan 31 + 1 day');
  assertEq(X.addDays('2026-12-31', 1), '2027-01-01', 'year rollover: Dec 31 + 1 day');
  assertEq(X.addDays('2026-03-01', -1), '2026-02-28', 'common year: Mar 1 - 1 day');
  assertEq(X.addDays('2028-02-28', 1), '2028-02-29', 'leap year: Feb 28 + 1 day');
  assertEq(X.addDays('2028-02-29', 1), '2028-03-01', 'leap year: Feb 29 + 1 day');
  assertEq(X.diffDays('2026-03-01', '2026-02-28'), 1, 'date diff: across a month = 1 day');
  assertEq(X.diffDays('2027-01-01', '2026-12-31'), 1, 'date diff: across a year = 1 day');
  assertEq(X.diffDays('2026-09-20', '2026-09-20'), 0, 'date diff: same day = 0');
  assertEq(X.addDays('2026-09-20', 0), '2026-09-20', 'adding 0 days changes nothing');

  // ---- interaction flow: add a task
  const before = X.Store.tasks().length;
  E('task-title').value = 'runtime smoke test task';
  E('task-prio').value = 'P0';
  E('task-due').value = X.todayISO();
  let addErr = null;
  try { fire(E('task-form'), 'submit', { preventDefault() {} }); } catch (e) { addErr = e; }
  assert(!addErr, 'submitting a new task does not throw', addErr ? String(addErr) : '');
  assertEq(X.Store.tasks().length, before + 1, 'the new task is written to the data');
  assertEq(X.Store.tasks()[0].priority, 'P0', 'the new task priority is stored correctly');
  assert(E('task-title').value === '', 'the input is cleared after adding', 'value is ' + JSON.stringify(E('task-title').value));

  // ---- interaction flow: toggle done / postpone / delete
  const tid = X.Store.tasks()[0].id;
  let toggleErr = null;
  try { X.onToggle(tid); } catch (e) { toggleErr = e; }
  assert(!toggleErr && X.Store.tasks()[0].done === true, 'toggling the done state takes effect', toggleErr ? String(toggleErr) : '');

  const oid = overdue0.length ? overdue0[0].id : tid;
  const dueBefore = (X.Store.tasks().filter(function (x) { return x.id === oid; })[0] || {}).due;
  let postErr = null;
  try { X.onPostpone(oid); } catch (e) { postErr = e; }
  const dueAfter = (X.Store.tasks().filter(function (x) { return x.id === oid; })[0] || {}).due;
  assert(!postErr && dueAfter > dueBefore, 'postponing an overdue item pushes the due date back', dueBefore + ' → ' + dueAfter);

  let delErr = null;
  try { X.onDelete(tid); } catch (e) { delErr = e; }
  assert(!delErr && X.Store.tasks().filter(function (x) { return x.id === tid; }).length === 0,
    'deleting a task takes effect', delErr ? String(delErr) : '');

  // ---- filtering does not change the data (view state only)
  const cntBefore = X.Store.tasks().length;
  ['open', 'done', 'P0', 'all'].forEach(function (f) {
    try { X.onFilter(f); } catch (e) { fail('filter ' + f + ' does not throw', String(e)); return; }
  });
  assertEq(X.Store.tasks().length, cntBefore, 'filtering does not modify the underlying data');

  // ---- export does not throw
  let expErr = null;
  try { X.exportJSON(); } catch (e) { expErr = e; }
  assert(!expErr, 'exporting JSON does not throw', expErr ? String(expErr) : '');

  // ---- CSV parsing (the main route for users bringing data over from Excel / Feishu / Notion)
  if (typeof X.parseCSV === 'function') {
    assertEq(X.parseCSV('标题,优先级\n买菜,P0\n写周报,P2\n').length, 3, 'CSV: header + 2 rows = 3 rows');
    assertEq(X.parseCSV('a,b\n"x,y",z\n')[1], ['x,y', 'z'], 'CSV: a comma inside quotes is not a separator');
    assertEq(X.parseCSV('a\n"他说 ""你好"""\n')[1], ['他说 "你好"'], 'CSV: escaped double quotes are restored');
    assertEq(X.parseCSV('\uFEFFa,b\r\n1,2\r\n')[0], ['a', 'b'], 'CSV: BOM + CRLF cleaned up correctly');
    assertEq(X.parseCSV('a,b\n1,2\n\n\n').length, 2, 'CSV: trailing blank lines dropped');
    assertEq(X.parseCSV('a,b\n,,\n1,2\n')[1], ['1', '2'], 'CSV: fully empty lines dropped');
    assertEq(X.parseCSV('').length, 0, 'CSV: an empty string returns 0 rows without crashing');

    assertEq(X.guessColumn(['任务', '优先级', '到期日'], X.CSV_FIELDS[0]), 0, 'column guess: Chinese 任务 -> title');
    assertEq(X.guessColumn(['Task', 'Level', 'Due'], X.CSV_FIELDS[1]), 1, 'column guess: English Level -> priority');
    assertEq(X.guessColumn(['甲', '乙'], { hints: ['不存在'] }), -1, 'column guess: no match returns -1');

    assertEq(X.normalizePriority('高'), 'P0', 'priority normalisation: 高 -> P0');
    assertEq(X.normalizePriority('紧急'), 'P0', 'priority normalisation: 紧急 -> P0');
    assertEq(X.normalizePriority('低'), 'P2', 'priority normalisation: 低 -> P2');
    assertEq(X.normalizePriority('常规'), 'P2', 'priority normalisation: 常规 -> P2');
    assertEq(X.normalizePriority('中'), 'P1', 'priority normalisation: 中 -> P1');
    assertEq(X.normalizePriority(''), 'P1', 'priority normalisation: empty -> P1 fallback');

    assertEq(X.normalizeDate('2026/9/5'), '2026-09-05', 'date normalisation: 2026/9/5 -> zero-padded');
    assertEq(X.normalizeDate('2026.9.5'), '2026-09-05', 'date normalisation: dot separators');
    assertEq(X.normalizeDate(''), '', 'date normalisation: empty -> empty string');

    // End to end: attach the parse result -> apply the import -> data really lands in the store
    const csvBefore = X.Store.tasks().length;
    const csvHeader = ['任务', '优先级', '到期日'];
    const csvRows = [['ImportRowA', '高', '2026-10-01'], ['ImportRowB', '低', '2026/10/02'], ['', '高', '2026-10-03']];
    const csvMap = { title: 0, priority: 1, due: 2, tag: -1 };
    X.State.csv = { header: csvHeader, rows: csvRows, map: csvMap };
    let csvErr = null;
    try { X.applyCsvImport(); } catch (e) { csvErr = e; }
    assert(!csvErr, 'CSV import does not throw', csvErr ? String(csvErr) : '');
    assertEq(X.Store.tasks().length, csvBefore + 2, 'CSV import adds 2 rows (the headerless line is skipped)');
    assertEq(X.Store.tasks()[0].title, 'ImportRowA', 'CSV import: the batch keeps the file row order and goes to the top');
    assertEq(X.Store.tasks()[1].title, 'ImportRowB', 'CSV import: the second row follows immediately');
    assertEq(X.Store.tasks()[0].priority, 'P0', 'CSV import: priority normalised to P0');
    assertEq(X.Store.tasks()[0].due, '2026-10-01', 'CSV import: date normalised to ISO');
    assertEq(X.Store.tasks()[1].due, '2026-10-02', 'CSV import: slash dates normalised to ISO too');
    assertEq(X.State.csv, null, 'CSV import clears the staging state afterwards');

    // A missing required column must be rejected with a prompt, not silently imported as blank tasks
    X.State.csv = { header: ['甲', '乙'], rows: [['1', '2']], map: { title: -1, priority: -1, due: -1, tag: -1 } };
    const alertsBefore = alerts.length;
    let rejectErr = null;
    try { X.applyCsvImport(); } catch (e) { rejectErr = e; }
    assert(!rejectErr, 'a CSV missing a required column does not throw', rejectErr ? String(rejectErr) : '');
    assert(alerts.length > alertsBefore, 'a CSV missing the title column shows the user a prompt', 'alert count +' + (alerts.length - alertsBefore));
    X.State.csv = null;
  } else {
    fail('CSV parsing is available', 'parseCSV is not exported -- this file may not be derived from workspace-skeleton.html');
  }

  // ---- rule 12: a full local store must not lose data silently
  if (typeof X.Store.save === 'function') {
    const warnEl = E('storage-warn');
    lsState.fail = true;                       // turn the storage-full switch on
    let quotaThrew = null;
    try { X.Store.save(); } catch (e) { quotaThrew = e; }
    let warnRefreshErr = null;
    // save() only persists and records the reason; presenting it is the render layer's job, via the single refresh entry
    try { X.refreshAll(); } catch (e) { warnRefreshErr = e; }
    lsState.fail = false;                      // turn it straight back off so later cases are unaffected
    assert(!quotaThrew, 'a failed storage write does not throw at the user (it should degrade internally)', quotaThrew ? String(quotaThrew) : '');
    assert(!warnRefreshErr, 'refreshAll does not throw while storage is failing', warnRefreshErr ? String(warnRefreshErr) : '');
    assert(!!X.Store.saveError, 'a failed storage write is recorded as saveError', X.Store.saveError ? 'recorded' : 'not recorded');
    assert(hasAny(warnEl.innerHTML, [/保存失败/, /save failed/i]),
      'the storage failure is rendered into the banner via refreshAll', 'innerHTML length ' + ((warnEl.innerHTML || '').length));
    assert(warnEl.classList.contains('is-on'), 'the warning banner is lit up (is-on)', '');
    // It must self-heal after recovery: a successful write plus a refresh clears the banner, or the user keeps seeing a false alarm
    let healErr = null;
    try { X.Store.save(); X.refreshAll(); } catch (e) { healErr = e; }
    assert(!healErr && !X.Store.saveError, 'saveError clears automatically once storage recovers', healErr ? String(healErr) : '');
    assert((warnEl.innerHTML || '') === '' && !warnEl.classList.contains('is-on'),
      'the warning banner collapses once storage recovers', '');
  }

  // ---- still renders after clearing (rule 10, item 4: empty state does not crash)
  let clearErr = null;
  try { X.clearAll(); } catch (e) { clearErr = e; }
  assert(!clearErr, 'clearing data does not throw', clearErr ? String(clearErr) : '');
  assertEq(X.Store.tasks().length, 0, 'the task count is 0 after clearing');
  assert(confirms.length >= 2, 'clearing asks for a second confirmation', confirms.length + ' confirm call(s)');
  let afterClearErr = null;
  try { X.refreshAll(); } catch (e) { afterClearErr = e; }
  assert(!afterClearErr, 'refresh does not break with empty data', afterClearErr ? String(afterClearErr) : '');
  const emptyHtml = E('today-body') ? E('today-body').innerHTML : '';
  assert(emptyHtml.length > 0, 'the today block still renders an empty state with no data', emptyHtml.length + ' chars');

  // ---- a second initialisation (simulated reload) does not throw and must not re-seed sample data
  const beforeReInit = X.Store.tasks().length;
  let reInitErr = null;
  try { for (const fn of domReady) await fn({}); } catch (e) { reInitErr = e; }
  assert(!reInitErr, 'a second initialisation does not throw', reInitErr ? String(reInitErr) : '');
  assertEq(X.Store.tasks().length, beforeReInit, 'a second initialisation does not re-seed sample data (idempotent)');

  report(results.some(function (r) { return !r.ok; }) ? 1 : 0);
}

function report(code) {
  const failed = results.filter(function (r) { return !r.ok; });
  results.forEach(function (r) {
    if (r.ok) console.log('  [PASS] ' + r.name + (r.detail ? '   --  ' + r.detail : ''));
    else console.log('  [FAIL] ' + r.name + (r.detail ? '   --  ' + r.detail : ''));
  });
  const summary = 'FAIL ' + failed.length + '  |  PASS ' + (results.length - failed.length);
  if (failed.length) {
    console.log('\n[FAIL] ' + summary + ' -- fix these and re-run\n');
    process.exit(1);
  }
  console.log('\n[OK] ' + summary + ' -- runtime behaviour is sound\n');
  process.exit(code || 0);
}

main().catch(function (e) {
  console.error('the runtime smoke test itself threw:', e && (e.stack || e.message));
  process.exit(1);
});
