#!/usr/bin/env python3
"""Render the README picture gallery from the catalogue records.

The README is written for readers who are not engineers. Its gallery shows
every catalogue record as a picture, a name and a one-line plain status. A
hand-written gallery would drift with the next record, so this one is
generated, like the technical parts table of docs/ENGINEERING_OVERVIEW.md.

    python3 scripts/render_readme_gallery.py --write   # rewrite the README block
    python3 scripts/render_readme_gallery.py --check   # exit 1 if it has drifted

Every picture is a concept render. Each one sits above a caption saying so,
because a concept render must never pass for the original part or a product.
The block reads `parts/<id>/media/gyroid.png` where the bionic gyroid-core
render exists, otherwise `parts/<id>/media/preview.png`, so re-rendering either
and rerunning `--write` is enough to refresh the pictures.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_parts_table import court, nom as table_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "catalog" / "parts"
README = ROOT / "README.md"

BEGIN = "<!-- BEGIN PART GALLERY -->"
END = "<!-- END PART GALLERY -->"
COLUMNS = 3

# Two records keep a French `name` that render_parts_table.py does not
# override. The README shows an English display name; the record is untouched.
DISPLAY_NAMES = {
    "993-ENG-BRACKET-0001": "Turbo engine center bracket, bionic PicoGK study",
    "993-ENG-MOUNTING-0001": "Turbo engine mount, bionic PicoGK cage study",
}

# Plain words for the validation ladder of catalog/schemas/part.schema.json.
STAGES = {
    "concept": "Design study",
    "dimensionally_reviewed": "Dimensions reviewed",
    "prototype_fitted": "Prototype fitted",
    "functionally_tested": "Functionally tested",
    "engineering_reviewed": "Engineering reviewed",
    "released": "Released",
}

# Plain words for the safety classes of SAFETY.md.
CLASSES = {
    "prohibited_pending_engineering": "blocked until a professional engineering review",
    "safety_critical": "safety-critical, blocked until a formal engineering review",
    "functional": "functional part, needs documented testing",
    "non_critical": "low-risk part, needs a fit check",
}

BLOCKED = ("prohibited_pending_engineering", "safety_critical")


def display_name(record: dict) -> str:
    name = DISPLAY_NAMES.get(record["part_id"], table_name(record))
    # Keep the head of the name: the part page carries the full title.
    return court(name.split(",")[0].split(" - ")[0], 60)


def print_kind(part_dir: Path) -> str | None:
    path = part_dir / "print" / "print.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("kind")


def caption(kind: str | None) -> str:
    if kind == "part_print":
        return "Concept model — not the original part; a print file exists, fit not checked"
    if kind == "mockup":
        return "Concept model — not the original part; display mock-up only, never for use"
    return "Concept model — not the original part, not a print file"


def load() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RECORDS.glob("*.json"))]


def cell(record: dict) -> str:
    part_id = record["part_id"].lower()
    part_dir = ROOT / "parts" / part_id
    # The gyroid-core render (parts/picogk-catalog/bionic/render_gyroid.py) shows
    # the bionic sandwich model when one exists; it is withdrawn for the one
    # record whose views are withdrawn (no gyroid.png there either).
    gyroid = part_dir / "media" / "gyroid.png"
    image = gyroid if gyroid.is_file() else part_dir / "media" / "preview.png"
    page = part_dir / "README.md"
    for required in (image, page):
        if not required.is_file():
            raise SystemExit(f"missing {required.relative_to(ROOT)} for {record['part_id']}")
    name = html.escape(display_name(record))
    stage = STAGES[record["validation"]["status"]]
    status = f"{stage}: {CLASSES[record['classification']['safety_class']]}"
    href = f"parts/{part_id}/README.md"
    src = image.relative_to(ROOT).as_posix()
    return ('<td align="center" valign="top" width="33%">'
            f'<a href="{href}"><img src="{src}" '
            f'alt="Concept render of {name}" width="240"></a><br>'
            f"<sub><i>{html.escape(caption(print_kind(part_dir)))}</i></sub><br>"
            f'<a href="{href}"><b>{name}</b></a><br>'
            f"<sub>{html.escape(status)}</sub></td>")


def block(records: list[dict]) -> str:
    stages = Counter(r["validation"]["status"] for r in records)
    classes = Counter(r["classification"]["safety_class"] for r in records)
    total = len(records)
    blocked = sum(classes[c] for c in BLOCKED)
    first = ("all of them are" if stages["concept"] == total
             else f"{stages['concept']} of them are")
    summary = (f"*{total} part records; {first} design studies (status `concept`). "
               f"{blocked} are blocked until a professional engineering review "
               f"({classes['prohibited_pending_engineering']} prohibited pending "
               f"engineering, {classes['safety_critical']} safety-critical). "
               f"{stages['released']} are released.*")
    out = [BEGIN, "",
           "> [!CAUTION]",
           "> Every picture below is a computer-generated concept model. It is not the",
           "> original Porsche part, not a validated part and not for sale.",
           "", summary, "", "<table>"]
    cells = [cell(r) for r in records]
    for i in range(0, len(cells), COLUMNS):
        out += ["<tr>"] + cells[i:i + COLUMNS] + ["</tr>"]
    out += ["</table>", "",
            "*Generated from `catalog/parts/*.json` by `scripts/render_readme_gallery.py`; "
            "click a part to see it next to the original.*", "", END]
    return "\n".join(out)


def replace(text: str, new: str) -> str:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit(f"README.md must contain {BEGIN} and {END} exactly once")
    before, rest = text.split(BEGIN)
    return before + new + rest.split(END, 1)[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = README.read_text(encoding="utf-8")
    expected = replace(text, block(load()))
    if args.write:
        if expected != text:
            README.write_text(expected, encoding="utf-8", newline="\n")
            print("README.md  part gallery rewritten")
        else:
            print("README.md  part gallery already up to date")
        return 0
    if expected != text:
        print("FAIL   the README part gallery no longer matches catalog/parts/.\n"
              "       rerun: python3 scripts/render_readme_gallery.py --write",
              file=sys.stderr)
        return 1
    print("OK   README.md, part gallery matches the catalogue records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
