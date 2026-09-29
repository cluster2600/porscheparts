#!/usr/bin/env python3
"""Deterministic generator for the PET107 print-buy-manufacture BOM.

Reads the master engine BOM (twins/m64-engine-system/bom/m64-bom-v1.json) and
the lane selection record (parts/m64-pet107-bom/selection-pet107.json), joins
them on bom_id_local, derives the evidence level per line from the master-BOM
evidence fields and source citations, and emits:

  parts/m64-pet107-bom/pet107-bom-v1.json
  parts/m64-pet107-bom/pet107-bom-v1.csv

Stdlib only. Output is deterministic (fixed field order, sorted nothing --
selection-file order is the authoritative line order). No line may claim
fitted/tested/safe/released/manufacturing-ready status: the status column is
fixed to the research-lane disclaimer.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOM_PATH = ROOT / "twins/m64-engine-system/bom/m64-bom-v1.json"
SELECTION_PATH = ROOT / "parts/m64-pet107-bom/selection-pet107.json"
OUT_JSON = ROOT / "parts/m64-pet107-bom/pet107-bom-v1.json"
OUT_CSV = ROOT / "parts/m64-pet107-bom/pet107-bom-v1.csv"

LINE_STATUS = (
    "candidate line - not fitted, not tested, not safe, not released, "
    "not manufacturing-ready (no metrology or physical validation)"
)
PROCESS_FIELDS = ("identity", "dims", "interfaces", "loads")
CSV_COLUMNS = [
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
]


class BomError(RuntimeError):
    """Controlled generator error."""


def derive_evidence_level(part: dict, selection: dict) -> str:
    """Map master-BOM evidence fields + citations onto the research-doc ladder.

    Rules (see selection-pet107.json mapping_rules):
      any field 'sourced' and a FACT_public citation present -> FACT_public
      else any field 'sourced' and a measured_source citation -> measured_source
      else any field 'sourced' -> SINGLE_SOURCE
      else -> UNKNOWN
    The lane judgement itself (that the part belongs to PET107 at all) is
    always ASSUMPTION-class and lives in selection_basis, never in this column.
    """
    fields = part.get("evidence", {})
    sourced = any(fields.get(f) == "sourced" for f in PROCESS_FIELDS)
    measured_source = any(fields.get(f) == "measured_source" for f in PROCESS_FIELDS)
    citations = " ".join(part.get("sources", []))
    if sourced:
        if "FACT_public" in citations:
            return "FACT_public"
        if measured_source or "measured_source" in citations or "torque_spec" in citations:
            return "measured_source"
        return "SINGLE_SOURCE"
    if measured_source:
        return "measured_source"
    return "UNKNOWN"


def build_lines() -> list[dict]:
    bom = json.loads(BOM_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    parts_by_id = {p["bom_id_local"]: p for p in bom["parts"]}

    sel_ids = [s["bom_id_local"] for s in selection["parts"]]
    dupes = {i for i in sel_ids if sel_ids.count(i) > 1}
    if dupes:
        raise BomError(f"duplicate selection ids: {sorted(dupes)}")
    missing = sorted(set(sel_ids) - set(parts_by_id))
    if missing:
        raise BomError(
            f"selection ids absent from master BOM: {missing}"
        )

    lines = []
    for n, sel in enumerate(selection["parts"], start=1):
        part = parts_by_id[sel["bom_id_local"]]
        level = derive_evidence_level(part, sel)
        for key, value in (
            ("decision", sel["decision"]),
            ("process", sel["process"]),
            ("process_params", sel["process_params"]),
            ("selection_basis", sel["selection_basis"]),
            ("caveats", sel["caveats"]),
        ):
            if not value:
                raise BomError(f"{sel['bom_id_local']}: empty {key}")
        lines.append(
            {
                "line_id": f"PET107-{n:03d}",
                "bom_id_local": part["bom_id_local"],
                "name": part["name"],
                "part_number": part.get("part_number") or "UNKNOWN",
                "subsystem": part["subsystem"],
                "quantity": part["quantity"],
                "decision": sel["decision"],
                "process": sel["process"],
                "process_params": sel["process_params"],
                "evidence_level": level,
                "evidence_fields": json.dumps(
                    part.get("evidence", {}), sort_keys=True
                ),
                "source_citations": " | ".join(part.get("sources", []))
                or "UNKNOWN",
                "selection_basis": sel["selection_basis"],
                "caveats": sel["caveats"],
                "status": LINE_STATUS,
            }
        )
    return lines


def write_outputs(lines: list[dict], selection: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "bom_id": "PET107-BOM-V1",
        "derived_from": "twins/m64-engine-system/bom/m64-bom-v1.json",
        "selection_record": "parts/m64-pet107-bom/selection-pet107.json",
        "generated_by": "scripts/generate_pet107_bom.py (deterministic rerun)",
        "status": LINE_STATUS,
        "evidence_level_legend": selection["evidence_ladder"],
        "line_count": len(lines),
        "lines": lines,
    }
    OUT_JSON.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(lines)


def main() -> int:
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    lines = build_lines()
    write_outputs(lines, selection)
    print(f"pet107-bom-v1: {len(lines)} lines -> {OUT_JSON.name}, {OUT_CSV.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
