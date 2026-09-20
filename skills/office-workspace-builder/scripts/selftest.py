#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py — regression tests for the smoke checker itself (office-workspace-builder)

Why this exists:
    smoke_check.py is the ruler. If the ruler is broken (say a rule's regex can never
    match), it will happily report PASS on bad code — and delivery quality depends on
    it. So every ruler has to be measured against known-bad input: for each known-bad
    sample the checker MUST report the matching FAIL, and for the known-good sample it
    MUST report zero FAIL.

Usage:
    python scripts/selftest.py            # run every case
    python scripts/selftest.py -v         # also print the checker's raw output

Exit code: 0 = every case behaved as expected; 1 = at least one did not.

Cases whose rule needs node (the JS syntax rule shells out to `node --check`) are reported as SKIP
when node is absent, never as failures -- node is optional, so a node-less run must still be honest
rather than alarming.
Standard library only.
"""

import io
import os
import re
import sys
import shutil
import contextlib
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.path.normpath(os.path.join(HERE, "..", "assets", "workspace-skeleton.html"))

C_RED, C_GRN, C_YEL, C_DIM, C_OFF = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"


def _stdout_is_tty():
    """Colour is for a human at a terminal; redirected or captured output stays plain."""
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


if not _stdout_is_tty() or os.environ.get("NO_COLOR"):
    C_RED = C_GRN = C_YEL = C_DIM = C_OFF = ""
elif os.name == "nt" and not os.environ.get("WT_SESSION"):
    C_RED = C_GRN = C_YEL = C_DIM = C_OFF = ""

# smoke_check.py downgrades the JS syntax rule to a WARN when node is missing (node is optional),
# so a sample that is supposed to be caught by that rule cannot be caught on a node-less machine.
NODE = shutil.which("node")
NEEDS_NODE = {"JS syntax error (bracket mismatch)"}


def _load_smoke():
    spec = importlib.util.spec_from_file_location("smoke_check", os.path.join(HERE, "smoke_check.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


smoke = _load_smoke()


def run_check(src_text):
    """Write the source to a temp file, run check_file once, return (exit code, output text)."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".html", prefix="selftest_")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(src_text)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = smoke.check_file(path, quiet=False)
        return code, buf.getvalue()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def fail_rules(out):
    """Pull the rule names that produced a [FAIL] out of the checker's output.

    Rule names contain spaces themselves, so split on runs of 2+ spaces.
    """
    out = ANSI_RE.sub("", out)
    return set(m.strip() for m in re.findall(r"\[FAIL\]\s+(.+?)\s{2,}", out))


def warn_rules(out):
    return set(m.strip() for m in re.findall(r"\[WARN\]\s+(.+?)\s{2,}", ANSI_RE.sub("", out)))


# ---------------------------------------------------------------- build bad samples

with open(SKELETON, "r", encoding="utf-8") as _f:
    GOOD = _f.read()

RADIUS_LINE = "--radius-lg:16px; --radius-md:10px; --radius-sm:6px; --radius-xs:4px;"


def inject_head_link(src):
    return src.replace("<head>", '<head>\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/x.css">', 1)


def inject_emoji(src):
    return src.replace("</body>", '<div class="card">Keep going \U0001F600</div>\n</body>', 1)


def flatten_radius(src):
    return src.replace(RADIUS_LINE, RADIUS_LINE.replace("16px", "8px").replace("10px", "8px")
                       .replace("6px", "8px").replace("4px", "8px"))


def inject_silent_catch(src):
    return src.replace("</body>",
                       "<script>function __t(){ try{localStorage.setItem(LSK+'data',1)}catch(e){} }</script>\n</body>", 1)


def inject_cycle(src):
    return src.replace("</body>",
                       "<script>function __a(){ __b(); } function __b(){ __a(); }</script>\n</body>", 1)


def inject_missing_dom(src):
    return src.replace("</body>", "<script>document.getElementById('__definitely_missing__');</script>\n</body>", 1)


def truncate_tail(src):
    """Keep half of the JS from the last <script> onwards -- reproduces a real half-written file."""
    idx = src.rfind("<script")
    if idx < 0:
        return src[: int(len(src) * 0.75)]
    return src[: idx + (len(src) - idx) // 2]


def inject_js_syntax_error(src):
    """Every tag is closed, but the JS itself is malformed -- exercises the true syntax-error path."""
    return src.replace("</body>",
                       "<script>function __bad( { return 1; }</script>\n</body>", 1)


def too_many_modules(src):
    return src.replace("</body>", "<!-- MODULE:5 START --><!-- MODULE:5 END -->\n</body>", 1)


def strip_csv(src):
    src = re.sub(r"function\s+parseCSV\s*\([^)]*\)\s*\{", "function __unused_parse(\u0029{", src, count=1)
    src = re.sub(r"<input[^>]*accept=[\"'][^\"']*csv[^\"']*[\"'][^>]*>", "", src, flags=re.I)
    return src


def strip_preset(src):
    return re.sub(r":root\[data-preset=[\"'][a-z]+[\"']\]\s*\{[^{}]*\}", "", src)


CASES = [
    # (case name, mutation, FAIL rule names that must be hit, WARN rule names that must be hit, expect zero FAIL)
    ("Baseline sample (skeleton as shipped)", lambda s: s, set(), set(), True),
    ("External CDN dependency",            inject_head_link,      {"Rule3 ext deps"},    set(),                False),
    ("Emoji used as an icon",              inject_emoji,          {"Rule3 icons"},             set(),                False),
    ("Fake border-radius tiers",           flatten_radius,        {"Rule11 design"},           set(),                False),
    ("Silently swallowed storage write",   inject_silent_catch,   {"Rule12 fail visible"}, set(),                False),
    ("Call graph has a cycle",             inject_cycle,          {"Rule9 call graph"},        set(),                False),
    ("DOM reference to a missing element", inject_missing_dom,    {"Rule10 DOM"},              set(),                False),
    ("File truncated (unclosed tags)",     truncate_tail,         {"Rule10 file integrity"},   set(),                False),
    ("JS syntax error (bracket mismatch)", inject_js_syntax_error, {"Rule10 JS syntax"},       set(),                False),
    ("More than 4 modules",                too_many_modules,      {"Rule7 scope gate"},        set(),                False),
    ("Missing CSV import entry point",     strip_csv,             set(),                       {"Data entry CSV"},   False),
    ("Missing layout preset block",        strip_preset,          set(),                       {"Rule11 presets"},   False),
]


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    if not os.path.isfile(SKELETON):
        print("{}Skeleton file not found: {}{}".format(C_RED, SKELETON, C_OFF))
        return 1

    passed, failed, skipped = 0, 0, 0
    print("\n{}Checker regression tests -- {} cases{}\n".format(C_DIM, len(CASES), C_OFF))

    for name, mutate, want_fail, want_warn, expect_clean in CASES:
        if name in NEEDS_NODE and not NODE:
            skipped += 1
            print("{}[SKIP] {:<38} node not installed -- this rule falls back to a WARN, "
                  "nothing to measure against{}".format(C_YEL, name, C_OFF))
            continue
        src = mutate(GOOD)
        code, out = run_check(src)
        got_fail = fail_rules(out)
        got_warn = warn_rules(out)

        problems = []
        if expect_clean:
            if code != 0 or got_fail:
                problems.append("expected zero FAIL, got: {}".format(", ".join(sorted(got_fail)) or "(non-zero exit code)"))
        else:
            missing = want_fail - got_fail
            if missing:
                problems.append("missed, expected FAIL not raised: {}".format(", ".join(sorted(missing))))
        missing_warn = want_warn - got_warn
        if missing_warn:
            problems.append("missed, expected WARN not raised: {}".format(", ".join(sorted(missing_warn))))

        ok = not problems
        if ok:
            passed += 1
            print("{}[OK]  {:<38} {}".format(C_GRN, name, "zero FAIL" if expect_clean else "caught as expected"))
        else:
            failed += 1
            print("{}[FAIL] {:<38} {}".format(C_RED, name, "; ".join(problems)))

        if verbose:
            for line in out.strip().splitlines():
                print("    {}| {}{}".format(C_DIM, line, C_OFF))
            print("")

    print("\n{}Checker regression: {} passed | {} failed | {} skipped{}".format(
        C_GRN if not failed else C_RED, passed, failed, skipped, C_OFF))
    if failed:
        print("{}The checker itself is broken: fix the ruler before trusting any delivery{}".format(C_RED, C_OFF))
        return 1
    if skipped:
        print("{}Note: {} case(s) skipped because node is not installed. node is optional, but without it "
              "the JS syntax rule and the runtime gate stay unverified -- install node and re-run for the "
              "full three gates.{}".format(C_YEL, skipped, C_OFF))
        print("{}Ruler is trustworthy for the cases that could be measured: no false positives on the good "
              "sample, every measurable bad sample caught{}".format(C_GRN, C_OFF))
    else:
        print("{}Ruler is trustworthy: no false positives on the good sample, every bad sample caught{}".format(C_GRN, C_OFF))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
