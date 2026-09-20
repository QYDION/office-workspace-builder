#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py — one-shot pre-delivery verification for office-workspace-builder

Runs three gates in sequence; the run fails as a whole if any gate fails:
  1. selftest.py       -- measure the ruler first: does the checker actually flag each known-bad sample?
  2. smoke_check.py    -- static checks: external deps / call cycles / DOM / module count / design / failure visibility / file integrity
  3. runtime_smoke.js  -- runtime checks: really executes the inlined JS (init / date boundaries / interactions / CSV / storage full)

Usage:
    python scripts/verify.py <workspace.html>
    python scripts/verify.py <workspace.html> --no-selftest    # skip the ruler self-test (faster)
Exit code: 0 = all gates passed; 1 = at least one failed.
"""

import os
import sys
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

C_RED, C_GRN, C_YEL, C_DIM, C_OFF = "\033[31m", "\033[32m", "\033[33m", "\033[2m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    C_RED = C_GRN = C_YEL = C_DIM = C_OFF = ""

PY = sys.executable


def run(label, cmd):
    print("\n{}{} {}{}".format(C_DIM, ">>", label, C_OFF))
    print("{}  $ {}{}".format(C_DIM, " ".join(cmd), C_OFF))
    r = subprocess.run(cmd, cwd=os.path.dirname(HERE), text=True)
    ok = (r.returncode == 0)
    print("{}  {} {}{}".format(C_GRN if ok else C_RED, "PASS" if ok else "FAIL", label, C_OFF))
    return ok


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    target = args[0]
    if not os.path.isfile(target):
        print("{}File not found: {}{}".format(C_RED, target, C_OFF))
        return 1
    # The child processes run with the skill root as their cwd, so resolve the path
    # here first — otherwise a relative path handed in by the caller would be missed.
    target = os.path.abspath(target)

    gates = []
    if "--no-selftest" not in argv:
        gates.append(("Ruler self-test (the checker must flag every known-bad sample)",
                      [PY, os.path.join(HERE, "selftest.py")]))
    gates.append(("Static checks (smoke_check)",
                  [PY, os.path.join(HERE, "smoke_check.py"), target]))
    node = shutil.which("node")
    if node:
        gates.append(("Runtime checks (runtime_smoke)",
                      [node, os.path.join(HERE, "runtime_smoke.js"), target]))
    else:
        print("{}[!] node not found -- skipping the runtime gate. That gate catches runtime bugs the "
              "static checks cannot see; install node and re-run when you can.{}".format(C_YEL, C_OFF))

    results = []
    for label, cmd in gates:
        results.append((label, run(label, cmd)))

    print("\n" + "=" * 64)
    for label, ok in results:
        print("  {} {} {}".format("[OK]  " if ok else "[FAIL]", C_GRN if ok else C_RED, label + C_OFF))
    failed = [l for l, ok in results if not ok]
    if failed:
        print("\n{}{} gate(s) failed -- fix them before delivering{}".format(C_RED, len(failed), C_OFF))
        return 1
    print("\n{}All {} gates passed -- ready to deliver{}".format(C_GRN, len(results), C_OFF))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
