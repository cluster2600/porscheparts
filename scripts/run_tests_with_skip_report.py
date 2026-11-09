#!/usr/bin/env python3
"""Run the unittest suite, report skips per reason and enforce a skip budget.

Issue #418: CI installs only requirements/requirements-check.txt, so tests that need OCP,
trimesh, gmsh, cadquery, usd-core and similar runtimes skip. This runner makes
those skips visible (grouped by reason, also written to $GITHUB_STEP_SUMMARY)
and, when SKIP_BUDGET_ENFORCE=1 (set in CI), fails if the number of skips
exceeds tests/skip-budget.json. Lower the budget when skips are removed; raise
it only in a reviewed change that says why.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Match `python -m unittest` from the repository root: scripts/ must not
# shadow modules that tests import by bare name.
if __name__ == "__main__" and sys.path and Path(sys.path[0]).resolve() == ROOT / "scripts":
    sys.path[0] = str(ROOT)
BUDGET = ROOT / 'tests' / 'skip-budget.json'


def summarise(skipped) -> list[tuple[str, int, list[str]]]:
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for test, reason in skipped:
        groups[' '.join(str(reason).split())].append(test.id().split('.')[0])
    rows = [(reason, len(ids), sorted(set(ids))) for reason, ids in groups.items()]
    return sorted(rows, key=lambda row: (-row[1], row[0]))


def report_lines(rows, total: int, budget: int | None) -> list[str]:
    lines = [f'## Test skips: {total}' + (f' (budget {budget})' if budget is not None else ''), '',
             '| skips | reason | modules |', '|---:|---|---|']
    for reason, count, modules in rows:
        shown = ', '.join(modules[:4]) + (f' (+{len(modules) - 4})' if len(modules) > 4 else '')
        lines.append(f'| {count} | {reason.replace("|", "/")} | {shown} |')
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--start', default='tests')
    parser.add_argument('--enforce', action='store_true',
                        default=os.environ.get('SKIP_BUDGET_ENFORCE') == '1')
    args = parser.parse_args(argv)

    suite = unittest.defaultTestLoader.discover(str(ROOT / args.start))
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    budget = json.loads(BUDGET.read_text())['max_skips']
    total = len(result.skipped)
    lines = report_lines(summarise(result.skipped), total, budget)
    print('\n'.join(lines), file=sys.stderr)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')

    if not result.wasSuccessful():
        return 1
    if args.enforce and total > budget:
        print(f'Skip budget exceeded: {total} skips > {budget} in {BUDGET.relative_to(ROOT)}. '
              'Make the new tests run in CI or name why they cannot, then raise the '
              'budget in a reviewed change.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
