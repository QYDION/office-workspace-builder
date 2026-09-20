#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_check.py — pre-delivery static smoke check for office workspaces (office-workspace-builder)

Static checks on a generated workspace HTML before delivery, catching the severe problems a machine can see:
  1. External dependencies (frameworks / CDN / fonts / chart libraries) --  rule 3
  2. Function call cycles / render functions calling each other  --  rule 9 (the main cause of a blank page via stack overflow)
  3. getElementById / querySelector targets missing from the HTML  --  rule 10
  4. Inline JS syntax errors (truncation, unbalanced brackets) --  rule 7 a common after-effect of incremental writes in rule 7
  5. More than 4 modules  --  rule 7 scope gate
  6. Missing mobile essentials  --  rule 4
  7. Missing sample data / backup entries / second confirmation  --  rule 2, 5, 6
  8. Emoji used as icons  --  rule 3
  9. Homogeneous design (untiered radii / a single shadow value / shadows on flat cards) --  rule 11
 10. Missing layout-preset mechanism  --  rule 11
 11. Storage failures swallowed silently  --  rule 12
 12. Missing data entry points (CSV import / GBK fallback) --  data has to get in before anyone uses it

Usage:
    python smoke_check.py <workspace.html> [more.html ...]
    python smoke_check.py <workspace.html> --quiet     # list only FAIL / WARN

Exit code: 0 = no FAIL; 1 = at least one FAIL. WARN does not affect the exit code.
Standard library only. When node is available it also runs a real JS syntax check; otherwise that step is skipped.
"""

import os
import re
import sys
import shutil
import subprocess
import tempfile

# ---------------------------------------------------------------- output helpers

C_RED = "\033[31m"
C_YEL = "\033[33m"
C_GRN = "\033[32m"
C_DIM = "\033[2m"
C_OFF = "\033[0m"


def _stdout_is_tty():
    """Colour is for a human at a terminal; redirected or captured output stays plain."""
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


if not _stdout_is_tty() or os.environ.get("NO_COLOR"):
    # Redirected output (a log file, a pipe) must stay clean: no ANSI escapes in it
    C_RED = C_YEL = C_GRN = C_DIM = C_OFF = ""
elif os.name == "nt" and not os.environ.get("WT_SESSION"):
    # Older Windows consoles do not always support ANSI; degrade to plain text to be safe
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        C_RED = C_YEL = C_GRN = C_DIM = C_OFF = ""


class Report:
    def __init__(self, path):
        self.path = path
        self.fails = []
        self.warns = []
        self.passes = []

    def fail(self, rule, msg):
        self.fails.append((rule, msg))

    def warn(self, rule, msg):
        self.warns.append((rule, msg))

    def ok(self, rule, msg=""):
        self.passes.append((rule, msg))


# ---------------------------------------------------------------- JS preprocessing

def strip_js(code):
    """Strip comments and string literals, but keep the expressions inside ${} template strings, so function calls can be extracted."""
    out = []
    i = 0
    n = len(code)
    prev_sig = ""  # last significant character, used to tell whether '/' starts a regex
    while i < n:
        c = code[i]
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            j = code.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            j = code.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c in "\"'":
            q = c
            i += 1
            while i < n and code[i] != q:
                if code[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append('""')
            prev_sig = '"'
            continue
        if c == "`":
            expr, i = _read_template(code, i, n)
            out.append(expr)
            prev_sig = "`"
            continue
        # Regex literals: a '/' after one of these characters starts a regex
        if c == "/" and prev_sig in ("", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "\n"):
            j = _read_regex(code, i, n)
            if j > i:
                i = j
                out.append("RE")
                prev_sig = "E"
                continue
        out.append(c)
        if not c.isspace():
            prev_sig = c
        i += 1
    return "".join(out)


def _read_template(code, i, n):
    """code[i] == '`'. Returns (concatenation of every ${} expression, new index)."""
    parts = []
    i += 1
    while i < n:
        c = code[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            i += 1
            break
        if c == "$" and i + 1 < n and code[i + 1] == "{":
            j = i + 2
            depth = 1
            while j < n and depth:
                cj = code[j]
                if cj == "\\":
                    j += 2
                    continue
                if cj in "\"'":
                    q = cj
                    j += 1
                    while j < n and code[j] != q:
                        if code[j] == "\\":
                            j += 1
                        j += 1
                    j += 1
                    continue
                if cj == "{":
                    depth += 1
                elif cj == "}":
                    depth -= 1
                j += 1
            parts.append(" " + code[i + 2: max(i + 2, j - 1)] + " ")
            i = j
            continue
        i += 1
    return "".join(parts), i


def _read_regex(code, i, n):
    """code[i] == '/' and looks like the start of a regex. Returns the index after the regex ends (or i unchanged if it is not a regex)."""
    j = i + 1
    in_class = False
    while j < n:
        c = code[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return i  # a newline means this is not a regex
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            return j + 1
        j += 1
    return i


FUNC_DEF_RE = re.compile(r"(?:^|[\s;{}()])function\s+([A-Za-z_$][\w$]*)\s*\(")
CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(")


def extract_functions(js):
    """Returns {function name: body source}"""
    out = {}
    for m in FUNC_DEF_RE.finditer(js):
        name = m.group(1)
        start = m.end() - 1  # points at '('
        body = _brace_body(js, start)
        if body is not None:
            out[name] = body
    return out


def _brace_body(js, paren_idx):
    """Starting at '(', find the matching ')' and then take the following {...} body."""
    n = len(js)
    i = paren_idx
    depth = 0
    while i < n:
        if js[i] == "(":
            depth += 1
        elif js[i] == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    j = i + 1
    while j < n and js[j].isspace():
        j += 1
    if j >= n or js[j] != "{":
        return ""
    depth = 0
    k = j
    while k < n:
        if js[k] == "{":
            depth += 1
        elif js[k] == "}":
            depth -= 1
            if depth == 0:
                return js[j: k + 1]
        k += 1
    return js[j:]  # unclosed: the classic symptom of a truncated incremental write


def find_cycles(graph):
    """DFS for cycles; returns [[a, b, ..., a], ...]"""
    cycles = []
    seen_cycles = set()
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict((k, WHITE) for k in graph)

    def dfs(node, stack):
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, ()):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                idx = stack.index(nxt)
                cyc = stack[idx:] + [nxt]
                key = tuple(sorted(cyc))
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(cyc)
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in list(graph):
        if color[node] == WHITE:
            dfs(node, [])
    return cycles


# ---------------------------------------------------------------- individual checks

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U0001F900-\U0001F9FF\uFE0F\u200D]"
)
# Unambiguous emoji-as-icon characters (the dingbats commonly pressed into service as emoji)
EMOJI_DINGBAT_RE = re.compile(
    "[\u2705\u274c\u2714\u2716\u2b50\u2b55\u2757\u2753\u2795\u2796\u23f0\u23f3"
    "\u2611\u2610\u267b\u267f\u2640\u2642\u2b06\u2b07\u27a1\u2b05]"
)
# Benign symbols common in typography; not treated as emoji icons
DINGBAT_RE = re.compile("[\u2600-\u27BF\u2B00-\u2BFF]")

EXTERNAL_FAIL_PATTERNS = [
    (re.compile(r"<script[^>]*\ssrc\s*=", re.I), "<script src=...> external script"),
    (re.compile(r"<link[^>]*\shref\s*=\s*[\"']?https?:", re.I), "<link href=http...> external stylesheet"),
    (re.compile(r"@import\s", re.I), "CSS @import of an external stylesheet"),
    (re.compile(r"url\(\s*[\"']?https?:", re.I), "CSS url(http...) external resource"),
    (re.compile(r"cdn\.|unpkg\.com|jsdelivr|cdnjs\.|bootstrapcdn|tailwindcss\.com|googleapis\.com|fonts\.gstatic", re.I),
     "references a CDN or external font service"),
    (re.compile(r"<img[^>]*\ssrc\s*=\s*[\"']?https?:", re.I), "<img src=http...> external image"),
]

KNOWN_LIBS = [
    (re.compile(r"\b(jquery|\$\.ajax|Chart\.js|new Chart\(|echarts\.init|bootstrap\.|Vue\.createApp|React\.createElement|tailwind\.config)", re.I),
     "looks like it depends on an external JS library (jQuery / Chart.js / ECharts / Bootstrap / Vue / React / Tailwind)"),
]


def check_external(src, rep):
    hit = False
    for rx, desc in EXTERNAL_FAIL_PATTERNS + KNOWN_LIBS:
        m = rx.search(src)
        if m:
            line = src[: m.start()].count("\n") + 1
            rep.fail("Rule3 ext deps", "line {}: {} -> `{}`".format(line, desc, m.group(0)[:70].strip()))
            hit = True
    if not hit:
        rep.ok("Rule3 ext deps", "no external dependencies found")


def check_emoji(src, rep):
    body = re.sub(r"<style[\s\S]*?</style>", "", src, flags=re.I)
    body = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.I)
    em = EMOJI_RE.search(body) or EMOJI_DINGBAT_RE.search(body)
    db = DINGBAT_RE.search(body)
    if em and db and db.start() == em.start():
        db = None  # one character at a time, so it is not reported twice
    if em:
        line = body[: em.start()].count("\n") + 1
        rep.fail("Rule3 icons", "emoji near line {} (use an inline SVG path instead): `{}`".format(line, em.group(0)))
    elif not db:
        rep.ok("Rule3 icons", "no emoji found")
    if db:
        if em:
            rep.warn("Rule3 icons", "other symbol characters whose purpose needs confirming: `{}`".format(db.group(0)))
        else:
            line = body[: db.start()].count("\n") + 1
            rep.warn("Rule3 icons", "symbol characters near line {} (typographic marks such as * are fine; if they act as icons, switch to inline SVG): `{}`".format(line, db.group(0)))


def check_scripts(src, rep):
    blocks = re.findall(r"<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)</script>", src, re.I)
    return "\n;\n".join(blocks)


def check_cycles(js, rep, raw_js=None):
    # The de-stringed copy is used for call-graph analysis; entry-point checks need the raw JS (otherwise 'DOMContentLoaded' is blanked out as a string)
    raw = raw_js if raw_js is not None else js
    clean = strip_js(js)
    funcs = extract_functions(clean)
    if not funcs:
        rep.warn("Rule9 call graph", "no function declarations parsed (if arrow-function assignments are used, check the call graph by hand)")
        return {}

    graph = {}
    for name, body in funcs.items():
        calls = set()
        for m in CALL_RE.finditer(body):
            callee = m.group(1)
            if callee in funcs and callee != name:
                calls.add(callee)
        graph[name] = calls

    cycles = find_cycles(graph)
    if cycles:
        for cyc in cycles:
            rep.fail("Rule9 call graph", "function call cycle detected (causes infinite recursion / stack overflow):" + " → ".join(cyc))
    else:
        rep.ok("Rule9 call graph", "no cycles ({} functions)".format(len(funcs)))

    bad = []
    for name, calls in graph.items():
        if not name.startswith("render"):
            continue
        for callee in calls:
            if callee.startswith("render") and name != "refreshAll":
                bad.append("{}() → {}()".format(name, callee))
    if bad:
        for b in bad:
            rep.fail("Rule9 render cross", "render functions must not call each other; all linkage goes through refreshAll():" + b)
    else:
        rep.ok("Rule9 render cross", "no cross-calls between render functions")

    if "refreshAll" not in funcs:
        has_alt = re.search(r"function\s+(updateView|renderAll)\s*\(", clean)
        if not has_alt:
            rep.warn("Rule9 refresh entry", "no unified refreshAll() entry point found")
        else:
            rep.ok("Rule9 refresh entry", "using an equivalent entry point " + has_alt.group(1) + "()")
    else:
        rep.ok("Rule9 refresh entry", "unified refreshAll() entry point present")

    if not re.search(r"DOMContentLoaded|window\.onload", raw):
        rep.fail("Rule10 init", "no DOMContentLoaded / window.onload init entry point")
    else:
        rep.ok("Rule10 init", "init entry point present")

    return graph


def check_dom_ids(src, rep):
    ids = set()
    for m in re.finditer(r"(?<![\w-])id\s*=\s*[\"']([^\"']+)[\"']", src):
        ids.add(m.group(1))
    refs = set()
    for m in re.finditer(r"getElementById\(\s*[\"']([^\"']+)[\"']\s*\)", src):
        refs.add(m.group(1))
    for m in re.finditer(r"querySelector(?:All)?\(\s*[\"']#([^\"']+)[\"']\s*\)", src):
        refs.add(m.group(1))
    # Data-driven navigation targets (MODULES[].target)
    for m in re.finditer(r"target\s*:\s*[\"']([^\"']+)[\"']", src):
        refs.add(m.group(1))

    missing = sorted(r for r in refs if r not in ids)
    if missing:
        rep.fail("Rule10 DOM", "referenced in JS but missing from the HTML:" + ", ".join("#" + x for x in missing))
    else:
        rep.ok("Rule10 DOM", "all {} element references exist".format(len(refs)))


def check_modules(src, rep):
    nums = sorted(set(int(x) for x in re.findall(r"<!--\s*MODULE:(\d+)\s*START", src)))
    if nums and max(nums) > 4:
        rep.fail("Rule7 scope gate", "{} modules ({}) exceeds the limit of 4; present a phased plan first".format(len(nums), nums))
    elif nums:
        rep.ok("Rule7 scope gate", "{} modules, within the limit".format(len(nums)))
    else:
        rep.warn("Rule7 scope gate", "no `<!-- MODULE:n START -->` marker found, so the module count cannot be checked automatically; confirm by hand that it is <= 4")


def check_mobile(src, rep):
    if not re.search(r"<meta[^>]*name=[\"']viewport[\"']", src, re.I):
        rep.fail("Rule4 responsive", "viewport meta tag missing; mobile browsers will render at desktop width")
    else:
        rep.ok("Rule4 responsive", "viewport declared")

    if not re.search(r"env\(\s*safe-area-inset-bottom\s*\)", src):
        rep.warn("Rule4 responsive", "env(safe-area-inset-bottom) not found; the bottom tab bar may sit under the iPhone home indicator")

    if not re.search(r"font-size\s*:\s*16px", src) and not re.search(r"font-size\s*:\s*1rem", src):
        rep.warn("Rule4 responsive", "no 16px input font size found (iOS zooms the page in when an input is focused)")

    if not (re.search(r"--tap\s*:\s*4[4-9]px|--tap\s*:\s*5\dpx", src)
            or re.search(r"min-height\s*:\s*(4[4-9]|[5-9]\d)px", src)
            or re.search(r"height\s*:\s*44px", src)):
        rep.warn("Rule4 responsive", "no 44px minimum tap target found (--tap / min-height:44px, etc.)")

    if not re.search(r"@media[^{]*max-width", src):
        rep.warn("Rule4 responsive", "no @media max-width breakpoint found; narrow screens may not stack into a single column")


# --- language-neutral block markers ---------------------------------------------------
# The skeleton carries these mandatory blocks under fixed ids, so one ruler covers workspaces in any UI language.
# UI strings (Chinese / English) act as a fallback for hand-written workspaces that do not reuse the skeleton ids.
# Only the visible markup is scanned (style/script removed), so identifiers in JS are not mistaken for UI copy.
MARKUP_RE_STYLE = re.compile(r"<style[\s\S]*?</style>", re.I)
MARKUP_RE_SCRIPT = re.compile(r"<script[\s\S]*?</script>", re.I)


def _markup_only(src):
    return MARKUP_RE_SCRIPT.sub("", MARKUP_RE_STYLE.sub("", src))


def _has_word(text, words):
    """Find a word in the text on word boundaries (case-insensitive), so exportJSON does not trip the export check."""
    for w in words:
        if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", text, re.I):
            return True
    return False


TODAY_ID_MARKERS = ('id="today-card"', "id='today-card'", 'id="today-body"', "id='today-body'")
BACKUP_EXPORT_ID_MARKERS = ('id="btn-export"', "id='btn-export'")
BACKUP_IMPORT_ID_MARKERS = ('id="btn-import"', "id='btn-import'")


def check_data_layer(src, rep):
    markup = _markup_only(src)
    if any(m in src for m in TODAY_ID_MARKERS) or "今天要处理" in src or _has_word(markup, ["Today"]):
        rep.ok("Rule5 today block", "pinned 'today' block is present")
    else:
        rep.fail("Rule5 today block", "pinned 'today' block missing (should carry id=\"today-card\") -- this is the workspace's core value")

    if not re.search(r"sampleData|seedSample|预置示例", src):
        rep.warn("Rule6 sample data", "no sample-data logic found (sampleData / seedSample)")
    else:
        rep.ok("Rule6 sample data", "sample-data logic present")

    has_export = any(m in src for m in BACKUP_EXPORT_ID_MARKERS) or "导出" in src or _has_word(markup, ["Export"])
    has_import = any(m in src for m in BACKUP_IMPORT_ID_MARKERS) or "导入" in src or _has_word(markup, ["Import"])
    if not (has_export and has_import):
        rep.fail("Rule2 backups", "first-screen backup entries missing (export {} / import {}; should carry id=\"btn-export\" / id=\"btn-import\")".format(
            "yes" if has_export else "no", "yes" if has_import else "no"))
    else:
        rep.ok("Rule2 backups", "export / import entries present")

    confirms = len(re.findall(r"\bconfirm\(", src))
    if confirms < 2:
        rep.warn("Rule2 backups", "only {} confirm() call(s) found; clearing data needs a second confirmation".format(confirms))
    else:
        rep.ok("Rule2 backups", "{} confirmation(s) present".format(confirms))

    m = re.search(r"[\"'`](wb_[A-Za-z0-9_]*)[\"'`]", src)
    if m:
        rep.ok("Rule1 storage", "localStorage key prefix is compliant: `{}`".format(m.group(1)))
    elif re.search(r"localStorage\s*\.\s*(setItem|getItem)", src):
        rep.warn("Rule1 storage", "localStorage is used but no `wb_`-prefixed key found; may collide with other pages on the same origin")
    else:
        rep.warn("Rule1 storage", "no localStorage usage detected (ignore if this is cloud-only mode)")


def check_integrity(src, rep):
    """File integrity: truncation is the usual result of a half-finished incremental write, and an unclosed <script> gets
    dropped wholesale by the regex, which silently disables every later JS check  --  so it has to be caught on its own."""
    problems = []
    n_open = len(re.findall(r"<script(?![^>]*\ssrc=)", src, re.I))
    n_close = len(re.findall(r"</script\s*>", src, re.I))
    if n_open != n_close:
        problems.append("script tag not closed ({} open / {} close)".format(n_open, n_close))
    if len(re.findall(r"<style", src, re.I)) != len(re.findall(r"</style\s*>", src, re.I)):
        problems.append("style tag not closed")
    for tag in ("body", "html"):
        if not re.search(r"</{}>".format(tag), src, re.I):
            problems.append("missing closing tag </{}>".format(tag))

    if problems:
        rep.fail("Rule10 file integrity", "the file looks truncated:" + "; ".join(problems) +
                 ". Rewrite following rule 7 (write the skeleton first, then add one module per call) and make sure every write completes.")
    else:
        rep.ok("Rule10 file integrity", "tags closed properly (script/style/body/html)")


def check_js_syntax(js, rep):
    if not js.strip():
        # Never run node --check on an empty string and then report PASS  --  that disguises 'unclosed and dropped' as 'syntax OK'
        rep.warn("Rule10 JS syntax", "no inlinable JS extracted, skipping (if the file is truncated, see the file-integrity check)")
        return
    node = shutil.which("node")
    if not node:
        rep.warn("Rule10 JS syntax", "node not available, skipping the JS syntax check -- confirm by hand that the file is not truncated")
        return
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".js")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            detail = (r.stderr or r.stdout or "").strip().splitlines()
            rep.fail("Rule10 JS syntax", "inline JS syntax error (the file may be truncated):" + (detail[0] if detail else "unknown"))
        else:
            rep.ok("Rule10 JS syntax", "inline JS syntax check passed")
    except Exception as e:  # node exists but the call failed
        rep.warn("Rule10 JS syntax", "JS syntax check could not run: {}".format(e))
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def parse_css_rules(src):
    """Coarse CSS rule parsing: returns [(selector, body), ...]. @media preludes show up as empty-body rules; filter as needed."""
    style = re.search(r"<style[^>]*>([\s\S]*?)</style>", src, re.I)
    if not style:
        return []
    css = re.sub(r"/\*[\s\S]*?\*/", "", style.group(1))
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def check_design(src, rep):
    """Rule 11: design must not be homogeneous -- radii should step down by tier and shadows must not be sprinkled everywhere."""
    rules = parse_css_rules(src)
    if not rules:
        rep.warn("Rule11 design", "no <style> rules parsed; skipping the design-homogeneity check")
        return

    # ---- 1. Radius tiers: exclude pills (>=100px) and circles (%); at least 3 are required
    tiers = set()
    for sel, body in rules:
        if sel.startswith("@"):
            continue
        for m in re.finditer(r"border-radius\s*:\s*([^;!]+)", body):
            v = m.group(1).strip()
            if "%" in v or v.lower() in ("0", "inherit", "initial", "unset"):
                continue
            hit = re.match(r"^(\d+(?:\.\d+)?)px$", v)
            if hit and float(hit.group(1)) >= 100:
                continue  # pill button, not a tier
            tiers.add(v)
    if len(tiers) < 3:
        rep.fail("Rule11 design", "only {} radius tier(s) ({}): containers / items / controls should step down, at least 3 tiers."
                 "one radius value shared by every element is the main source of a templated look".format(
                     len(tiers), ", ".join(sorted(tiers)) if tiers else "none"))
    else:
        rep.ok("Rule11 design", "{} radius tiers: {}".format(len(tiers), ", ".join(sorted(tiers))))

    # ---- 2. Are the radius tokens really tiered? (lg/md/sm all equal to one value = fake tiering)
    # Only the base `:root{...}` block: preset blocks (:root[data-preset=...]) override same-named tokens, so
    # scanning globally would read a preset's value as the baseline and produce a false conclusion.
    base = ""
    for sel, body in rules:
        if sel.strip() == ":root":
            base = body
            break
    tv = {}
    for m in re.finditer(r"(--radius-(?:lg|md|sm|xs))\s*:\s*([0-9.]+)px", base or src):
        tv[m.group(1)] = m.group(2)
    if len(tv) >= 2:
        if len(set(tv.values())) < 2:
            rep.fail("Rule11 design", "every radius token equals the same value ({}), so there is no tiering at all".format(
                ", ".join("%s=%spx" % kv for kv in sorted(tv.items()))))
        else:
            rep.ok("Rule11 design", "radius tokens are tiered properly:" + ", ".join("%s=%spx" % kv for kv in sorted(tv.items())))

    # ---- 3. Shadow value count: 1 value used everywhere = zero depth information
    shadows = set()
    for sel, body in rules:
        if sel.startswith("@"):
            continue
        for m in re.finditer(r"box-shadow\s*:\s*([^;!]+)", body):
            shadows.add(m.group(1).strip())
    if len(shadows) == 1:
        rep.fail("Rule11 design", "only 1 box-shadow value ({}): shadows are a scarce resource,"
                 "flat cards should use borders only; keep shadows for raised layers".format(list(shadows)[0]))
    elif not shadows:
        rep.ok("Rule11 design", "no shadows used; flat layers are separated by borders")
    else:
        rep.ok("Rule11 design", "{} shadow tier(s), not overused on flat cards".format(len(shadows)))

    # ---- 4. Flat cards must not carry a non-none shadow
    for sel, body in rules:
        if sel.startswith("@") or not re.search(r"\.card(\b|$)", sel):
            continue
        m = re.search(r"box-shadow\s*:\s*([^;!]+)", body)
        if not m:
            continue
        v = m.group(1).strip()
        if v != "none" and "shadow-card" not in v:
            rep.fail("Rule11 design", "flat card `.card` carries a non-none shadow ({}) -- "
                     "keep shadows for raised layers only (sticky bar / today block / overlays)".format(v))


def _blank_literals(js):
    """Replace strings / templates / comments with equal-length spaces so character offsets stay put, which makes structural scanning easier."""
    out = list(js)
    i, n = 0, len(js)
    prev_sig = ""
    while i < n:
        c = js[i]
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            j = js.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            j = js.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c in "\"'":
            q = c
            j = i + 1
            while j < n and js[j] != q:
                if js[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            for k in range(i, j):
                out[k] = " "
            i = j
            prev_sig = '"'
            continue
        if c == "`":
            j = i + 1
            while j < n:
                if js[j] == "\\":
                    j += 2
                    continue
                if js[j] == "`":
                    j += 1
                    break
                j += 1
            for k in range(i, min(j, n)):
                out[k] = " "
            i = j
            prev_sig = "`"
            continue
        if c == "/" and prev_sig in ("", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "\n"):
            j = _read_regex(js, i, n)
            if j > i:
                for k in range(i, j):
                    out[k] = " "
                i = j
                prev_sig = "E"
                continue
        if not c.isspace():
            prev_sig = c
        i += 1
    return "".join(out)


def _match_brace(text, open_idx):
    """text[open_idx] == '{': returns (inner text, index after the closing brace); on mismatch returns (None, open_idx)."""
    depth = 0
    i, n = open_idx, len(text)
    while i < n:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i + 1
        i += 1
    return None, open_idx


def _iter_try_catch(blanked, raw):
    """Pair try/catch precisely; returns [(try_body_raw, catch_body_raw, catch_start)].

    Note: Structurelocating uses blanked (strings/comments wiped so bracket counting is accurate),
    but the body must be taken from raw  --  otherwise a comment inside a catch counts as blank and it is always judged an empty catch.
    The two have equal length, so offsets line up.
    """
    pairs = []
    for m in re.finditer(r"\btry\s*\{", blanked):
        open_idx = m.end() - 1
        tb, after = _match_brace(blanked, open_idx)
        if tb is None:
            continue
        cm = re.match(r"\s*catch\s*\([^)]*\)\s*\{", blanked[after:after + 80])
        if not cm:
            continue
        cstart = after + cm.end() - 1
        cb, _ = _match_brace(blanked, cstart)
        if cb is None:
            continue
        pairs.append((raw[open_idx + 1:open_idx + 1 + len(tb)],
                      raw[cstart + 1:cstart + 1 + len(cb)],
                      cstart))
    return pairs


def check_failure_visibility(src, js, rep):
    """rule 12: failures must be visible to the user. An empty catch is a choice that has to be declared explicitly.

    Decision rules:
      - catch contains real handling code                      -> pass
      - catch carries the @silent-ok marker (explicitly declared ignorable)-> pass
      - catch swallows a main-data write failure                     -> FAIL
      - catch swallows a secondary write / is completely empty / holds only a comment        -> WARN
    """
    blanked = _blank_literals(js)
    pairs = _iter_try_catch(blanked, js)
    hard, soft, declared = [], [], 0

    for try_body, catch_body, cstart in pairs:
        code = re.sub(r"/\*[\s\S]*?\*/", "", catch_body)
        code = re.sub(r"//[^\n]*", "", code).strip()
        if code:
            continue                         # real handling present
        if "@silent-ok" in catch_body:
            declared += 1
            continue                         # the author explicitly declared this failure ignorable
        line = js[:cstart].count("\n") + 1
        # The test for a main-data write: the first argument of setItem mentions the data key,
        # rather than merely stringifying something: --  the latter would misjudge secondary writes such as an offline queue as the main data.
        if re.search(r"localStorage\s*\.\s*setItem\s*\(\s*[^,]*data", try_body):
            hard.append((line, "main data write failure swallowed completely"))
        elif re.search(r"localStorage\s*\.\s*setItem", try_body):
            soft.append((line, "secondary localStorage write failure swallowed without declaring it"))
        elif catch_body.strip() == "":
            soft.append((line, "completely empty catch, not even a reason recorded"))
        else:
            soft.append((line, "catch contains only a comment and no handling"))

    if hard:
        for line, what in hard:
            rep.fail("Rule12 fail visible", "line {}: {} -- the user will think it saved, then lose everything on refresh".format(line, what))
    if soft:
        rep.warn("Rule12 fail visible", "line {}: {}. If it really is ignorable, declare it explicitly with `@silent-ok` inside the catch".format(
            ", ".join(str(l) for l, _ in soft[:5]), soft[0][1]))
    if not hard and not soft:
        rep.ok("Rule12 fail visible", "every catch either handles the error or declares it explicitly ({} @silent-ok)".format(declared))

    if re.search(r"localStorage\s*\.\s*setItem", js):
        if re.search(r"saveError|storage-warn|保存失败|写入失败", js):
            rep.ok("Rule12 fail visible", "storage failures have a user-visible outlet (saveError / warning banner)")
        else:
            rep.fail("Rule12 fail visible", "localStorage is written to, but there is no user-visible 'save failed' outlet")


def check_preset(src, rep):
    """Rule 11: is the layout-preset mechanism in place?"""
    n = len(re.findall(r":root\[data-preset=[\"'][a-z]+[\"']\]", src))
    if n == 0:
        rep.warn("Rule11 presets", "no :root[data-preset=...] preset block found; the layout may be hard-wired to one variation,"
                 "so it cannot be varied for a different scenario")
    elif n < 3:
        rep.warn("Rule11 presets", "only {} preset(s) defined; add the full calm / dense / report set".format(n))
    else:
        rep.ok("Rule11 presets", "{} layout presets present".format(n))

    if re.search(r"<html[^>]*data-preset=[\"'][a-z]+[\"']", src, re.I):
        rep.ok("Rule11 presets", "the html tag carries an initial data-preset value, so the first paint will not flash the default styles")
    else:
        rep.warn("Rule11 presets", "the html tag has no initial data-preset value, so the first paint may flash the default styles")


def check_data_entry(src, rep):
    """Data has to get in before anyone uses it: the CSV / Excel import path."""
    has_parser = bool(re.search(r"function\s+parseCSV", src))
    has_input = bool(re.search(r"<input[^>]*accept=[\"'][^\"']*csv", src, re.I))
    if has_parser and has_input:
        rep.ok("Data entry CSV", "CSV import path present (parseCSV + a csv file input)")
    elif has_parser or has_input:
        rep.warn("Data entry CSV", "CSV import path incomplete (parser {}, file input {})".format(
            "yes" if has_parser else "no", "yes" if has_input else "no"))
    else:
        rep.warn("Data entry CSV", "no CSV import capability -- users moving data over from Excel / Feishu / Notion will be stuck here")

    if re.search(r"gbk|GBK|TextDecoder", src):
        rep.ok("Data entry CSV", "handles GBK from Chinese Excel exports")
    else:
        rep.warn("Data entry CSV", "no GBK decode fallback -- CSV exported from Chinese Excel is not UTF-8 by default and will come out garbled")


# ---------------------------------------------------------------- main flow

def check_file(path, quiet=False):
    rep = Report(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="replace") as f:
            src = f.read()
    except OSError as e:
        print("{}Cannot read file: {} ({}){}".format(C_RED, path, e, C_OFF))
        return 1

    # Pure ASCII separator: a box-drawing glyph renders as mojibake on consoles whose code page
    # is not UTF-8, and a checker that looks broken gets distrusted for no reason.
    print("\n{}{} {} {}".format(C_DIM, "=" * 60, os.path.basename(path), C_OFF))
    print("{}path: {} | size: {:,} bytes | lines: {:,}{}".format(
        C_DIM, os.path.abspath(path), len(src.encode("utf-8")), src.count("\n") + 1, C_OFF))

    js = check_scripts(src, rep)
    if not js.strip():
        rep.warn("Structure", "no inline <script> content parsed; confirm that all logic really is inlined")

    check_external(src, rep)
    check_emoji(src, rep)
    check_cycles(js, rep, raw_js=js)
    check_dom_ids(src, rep)
    check_modules(src, rep)
    check_mobile(src, rep)
    check_data_layer(src, rep)
    check_design(src, rep)
    check_preset(src, rep)
    check_failure_visibility(src, js, rep)
    check_data_entry(src, rep)
    check_integrity(src, rep)
    check_js_syntax(js, rep)

    for rule, msg in rep.fails:
        print("{}[FAIL]{} {:<24} {}".format(C_RED, C_OFF, rule, msg))
    if not quiet:
        for rule, msg in rep.warns:
            print("{}[WARN]{} {:<24} {}".format(C_YEL, C_OFF, rule, msg))
        for rule, msg in rep.passes:
            print("{}[PASS]{} {:<24} {}".format(C_GRN, C_OFF, rule, msg))
    elif rep.warns:
        print("{}[WARN]{} {} warning(s); drop --quiet to see the detail".format(C_YEL, C_OFF, len(rep.warns)))

    summary = "FAIL {}  |  WARN {}  |  PASS {}".format(len(rep.fails), len(rep.warns), len(rep.passes))
    if rep.fails:
        print("{}[FAIL] {} -- fix these and re-run{}".format(C_RED, summary, C_OFF))
        return 1
    print("{}[OK] {} -- ready to deliver{}".format(C_GRN, summary, C_OFF))
    return 0


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in argv or "-q" in argv
    if not args:
        print(__doc__)
        return 2
    code = 0
    for p in args:
        if not os.path.isfile(p):
            print("{}File not found: {}{}".format(C_RED, p, C_OFF))
            code = 1
            continue
        code |= check_file(p, quiet=quiet)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
