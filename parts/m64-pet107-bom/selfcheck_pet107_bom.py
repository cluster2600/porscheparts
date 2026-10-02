#!/usr/bin/env python3
"""Self-check for the PET107 BOM deliverable (stdlib only).

Validates pet107-bom-v1.json against the inline schema below and the
CSV mirror, then enforces the lane evidence rules:

  R1  every line carries an evidence_level from the fixed ladder;
  R2  unevidenced lines/fields say UNKNOWN explicitly (no blanks);
  R3  no line claims fitted/tested/safe/released/manufacturing-ready
      outside the fixed negated status disclaimer;
  R4  print lines name a process (FDM/FFF PETG-PET-class or UNKNOWN);
      buy lines are buy-catalog;
  R5  quantities are positive integers;
  R6  CSV and JSON carry identical line counts and column values.

Exit 0 = pass. Any violation prints a line and exits 1.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JSON_PATH = HERE / "pet107-bom-v1.json"
CSV_PATH = HERE / "pet107-bom-v1.csv"
SELECTION_PATH = HERE / "selection-pet107.json"

ALLOWED_LEVELS = {
    "FACT_public",
    "measured_source",
    "CROSSCHECKED",
    "SINGLE_SOURCE",
    "ASSUMPTION",
    "UNKNOWN",
}
ALLOWED_DECISIONS = {"print", "buy"}
ALLOWED_PROCESSES = {
    "FDM/FFF PETG-PET-class",
    "buy-catalog (commercial consumable)",
    "UNKNOWN",
}
STATUS_DISCLAIMER = (
    "candidate line - not fitted, not tested, not safe, not released, "
    "not manufacturing-ready (no metrology or physical validation)"
)
CLAIM_WORDS = ("fitted", "tested", "safe", "released", "manufacturing-ready")
SCHEMA = {
    "required_top": [
        "schema_version",
        "bom_id",
        "derived_from",
        "selection_record",
        "status",
        "line_count",
        "lines",
    ],
    "required_line": [
        "line_id",
        "bom_id_local",
        "name",
        "part_number",
        "subsystem",
        "quantity",
        "decision",
        "process",
        "process_params",
        "evidence_level",
        "evidence_fields",
        "source_citations",
        "selection_basis",
        "caveats",
        "status",
    ],
    "line_id_pattern": r"^PET107-\d{3}$",
}

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def main() -> int:
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

    for key in SCHEMA["required_top"]:
        if key not in doc:
            err(f"schema: missing top-level key '{key}'")
    lines = doc.get("lines", [])
    if doc.get("line_count") != len(lines):
        err(f"schema: line_count {doc.get('line_count')} != len(lines) {len(lines)}")
    if len(lines) < 1:
        err("schema: no lines")

    pat = re.compile(SCHEMA["line_id_pattern"])
    seen_ids: set[str] = set()
    for line in lines:
        lid = line.get("line_id", "?")
        for key in SCHEMA["required_line"]:
            if key not in line:
                err(f"{lid}: missing field '{key}'")
        if not pat.match(lid):
            err(f"line_id '{lid}' does not match {SCHEMA['line_id_pattern']}")
        if lid in seen_ids:
            err(f"{lid}: duplicate line_id")
        seen_ids.add(lid)
        # R1 evidence level
        if line.get("evidence_level") not in ALLOWED_LEVELS:
            err(f"{lid}: evidence_level '{line.get('evidence_level')}' off-ladder")
        # R2 no blanks; unevidenced must be UNKNOWN
        for key in SCHEMA["required_line"]:
            if line.get(key) in (None, ""):
                err(f"{lid}: field '{key}' is blank; must be UNKNOWN")
        # R3 status disclaimer, no naked claims
        if line.get("status") != STATUS_DISCLAIMER:
            err(f"{lid}: status is not the fixed disclaimer")
        for field in ("name", "selection_basis", "caveats", "source_citations"):
            text = str(line.get(field, "")).lower()
            for word in CLAIM_WORDS:
                for m in re.finditer(word, text):
                    window = text[max(0, m.start() - 12): m.start()]
                    if "not " not in window:
                        err(
                            f"{lid}: field '{field}' claims '{word}' without "
                            "a preceding 'not '"
                        )
        # R4 decision/process coherence
        if line.get("decision") not in ALLOWED_DECISIONS:
            err(f"{lid}: decision '{line.get('decision')}' off-enum")
        if line.get("process") not in ALLOWED_PROCESSES:
            err(f"{lid}: process '{line.get('process')}' off-enum")
        if line.get("decision") == "print" and line.get("process") == (
            "buy-catalog (commercial consumable)"
        ):
            err(f"{lid}: print line with buy-catalog process")
        if line.get("decision") == "buy" and line.get("process") != (
            "buy-catalog (commercial consumable)"
        ):
            err(f"{lid}: buy line must name buy-catalog process")
        # R5 quantity
        qty = line.get("quantity")
        if not isinstance(qty, int) or qty < 1:
            err(f"{lid}: quantity {qty!r} is not a positive integer")

    # R6 CSV mirror
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != len(lines):
        err(f"csv: {len(rows)} rows != {len(lines)} json lines")
    for row, line in zip(rows, lines):
        for col, value in line.items():
            if row.get(col) != str(value):
                err(f"csv/json mismatch at {line.get('line_id')}.{col}")

    # selection coverage
    sel_ids = {s["bom_id_local"] for s in selection.get("parts", [])}
    bom_ids = {line.get("bom_id_local") for line in lines}
    if sel_ids != bom_ids:
        err(f"selection/BOM id mismatch: {sorted(sel_ids ^ bom_ids)}")

    if errors:
        print("SELF-CHECK FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print(f"SELF-CHECK PASS: {len(lines)} lines, {len(SCHEMA['required_line'])} "
          "fields, csv mirror consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
