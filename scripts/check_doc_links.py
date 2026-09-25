#!/usr/bin/env python3
"""Find broken relative links and anchors in the repository's Markdown.

Translating a page renames its headings, and every `page.md#old-heading` link
pointing at it silently stops working: GitHub opens the page at the top and
nobody notices. This script resolves every relative link in tracked Markdown
files, and every `#anchor` against the headings of its target, using GitHub's
slug rules.

    python3 scripts/check_doc_links.py            # report broken links
    python3 scripts/check_doc_links.py --strict   # exit 1 if any

Files under `evidence/` and `archive/` are skipped as sources: they are pinned
and cannot be fixed in place. Links *into* them are still checked.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
HTML_SRC = re.compile(r"<(?:img|a)\s[^>]*(?:src|href)=\"([^\"]+)\"", re.I)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.M)
EXPLICIT = re.compile(r"<a\s+(?:name|id)=\"([^\"]+)\"", re.I)


def slug(text: str) -> str:
    """GitHub's heading slug: lower-case, drop punctuation, spaces to hyphens."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.U)
    return text.replace(" ", "-")


def anchors(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        text = FENCE.sub("", path.read_text(encoding="utf-8", errors="replace"))
        seen: Counter = Counter()
        found = set(EXPLICIT.findall(text))
        for _, title in HEADING.findall(text):
            s = slug(title)
            found.add(s if not seen[s] else f"{s}-{seen[s]}")
            seen[s] += 1
        cache[path] = found
    return cache[path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    files = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout.split()
    cache: dict[Path, set[str]] = {}
    broken = []
    for f in files:
        parts = f.split("/")
        if "evidence" in parts or parts[0] == "archive":
            continue
        src = ROOT / f
        text = FENCE.sub("", src.read_text(encoding="utf-8", errors="replace"))
        targets = [m[0] or m[1] for m in LINK.findall(text)] + HTML_SRC.findall(text)
        for target in targets:
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
                continue
            path_part, _, frag = target.partition("#")
            dest = (src.parent / unquote(path_part)).resolve() if path_part else src
            if path_part and not dest.exists():
                broken.append((f, target, "missing file"))
                continue
            if frag and dest.suffix == ".md" and dest.is_file():
                if unquote(frag).lower() not in anchors(dest, cache):
                    broken.append((f, target, "missing anchor"))
    for f, target, why in broken:
        print(f"{why:<15} {f}  ->  {target}")
    print(f"\n{len(broken)} broken link(s) in {len(files)} Markdown files")
    return 1 if a.strict and broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
