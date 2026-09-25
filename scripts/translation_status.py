#!/usr/bin/env python3
"""Measure how much of the repository's Markdown is still written in French.

The translation to English is phased (see docs/TRANSLATION.md). This script is
its progress meter: it classifies every tracked Markdown file by comparing the
frequency of common French and English function words in its prose, code blocks
and inline code removed. It is a heuristic, not a linguist; a file that mixes
both languages is reported as "mixed" so a human looks at it.

    python3 scripts/translation_status.py            # summary by area
    python3 scripts/translation_status.py --list     # also list French/mixed files

Files under `evidence/` and `archive/` are counted separately: they are pinned
by SHA-256 digest and are never translated in place.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FRENCH = set("""le la les un une des du de et est sont dans pour par sur avec qui que
ne pas plus au aux ce cette ces son sa ses leur leurs il elle on nous vous ou où
mais donc car reste être été fait comme sans entre depuis chaque aucun aucune
lorsque dont""".split())
ENGLISH = set("""the a an and is are in for by on with which that not no more to this
these its their it we you or but so because remains be been done as without
between since each none when whose of from has have""".split())

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
WORD = re.compile(r"[a-zàâäçéèêëîïôöùûüœ']+", re.I)


def classify(text: str) -> str:
    prose = LINK_TARGET.sub("]", INLINE.sub(" ", FENCE.sub(" ", text)))
    words = [w.lower().strip("'") for w in WORD.findall(prose)]
    fr = sum(w in FRENCH for w in words)
    en = sum(w in ENGLISH for w in words)
    if fr + en < 20:
        return "too short"
    share = fr / (fr + en)
    if share > 0.7:
        return "french"
    if share < 0.3:
        return "english"
    return "mixed"


def area(path: str) -> str:
    parts = path.split("/")
    if "evidence" in parts or parts[0] == "archive":
        return "pinned (evidence/, archive/)"
    if len(parts) == 1:
        return "top level"
    if parts[0] == "docs" and len(parts) > 2:
        return f"docs/{parts[1]}/"
    return f"{parts[0]}/"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list French and mixed files")
    a = ap.parse_args()

    files = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout.split()
    by_area: dict[str, Counter] = defaultdict(Counter)
    pending: dict[str, list[str]] = defaultdict(list)
    for f in files:
        verdict = classify((ROOT / f).read_text(encoding="utf-8", errors="replace"))
        by_area[area(f)][verdict] += 1
        if verdict in ("french", "mixed"):
            pending[area(f)].append(f"{verdict:<7} {f}")

    total = Counter()
    print(f"{'area':<34} {'english':>8} {'mixed':>6} {'french':>7} {'short':>6}")
    for name in sorted(by_area, key=lambda n: (n.startswith("pinned"), n)):
        c = by_area[name]
        if not name.startswith("pinned"):
            total += c
        print(f"{name:<34} {c['english']:>8} {c['mixed']:>6} {c['french']:>7} {c['too short']:>6}")
    done = total["english"]
    todo = total["french"] + total["mixed"]
    print(f"\ntranslatable files: {done} in English, {todo} still French or mixed "
          f"({100 * done / max(done + todo, 1):.0f}% done); pinned files are never translated in place")

    if a.list:
        for name in sorted(pending):
            if name.startswith("pinned"):
                continue
            print(f"\n{name}")
            for line in sorted(pending[name]):
                print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
