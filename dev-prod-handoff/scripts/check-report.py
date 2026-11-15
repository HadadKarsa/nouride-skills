#!/usr/bin/env python3
"""Validate a dev report against the fixed format.

Usage: check-report.py <file>   or   check-report.py -   (stdin)
Exit 0 only when every required field is present and the commit is a full SHA.
"""
import re
import sys

REQUIRED = ["repo", "branch", "commit", "changes", "build", "test", "port", "health", "risk", "pending"]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check-report.py <file>|-", file=sys.stderr)
        return 2
    src = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()

    fields = {}
    for line in src.splitlines():
        m = re.match(r"^([a-z]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()

    problems = []
    for key in REQUIRED:
        if key not in fields:
            problems.append(f"missing field: {key}")
        elif not fields[key] or fields[key].startswith("<"):
            problems.append(f"empty or placeholder: {key}")

    commit = fields.get("commit", "")
    if commit and not re.fullmatch(r"[0-9a-f]{40}", commit):
        problems.append(f"commit is not a full 40-character sha: {commit!r}")

    branch = fields.get("branch", "")
    if branch and branch in ("main", "master"):
        problems.append("branch is the deploy branch; the dev must push feat/<topic>")

    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    print("OK report is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
