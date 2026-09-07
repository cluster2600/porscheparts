#!/usr/bin/env python3
"""Fast private p-curve-only probe for a native OCCT B-Rep.

The full F50 audit remains authoritative.  This probe intentionally enables
only ``CurveOnSurfaceMode`` to provide an early, non-release diagnostic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-brep", type=Path, required=True)
    parser.add_argument("--helper-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.helper_dir))
    from repair_pcurves_f42_2 import pcurve_fault_map

    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape, str(args.input_brep), BRep_Builder()):
        raise RuntimeError("native_BREP_read_failed")
    result = pcurve_fault_map(shape)
    report = {
        "schema": "porsche-917-f50-private-native-pcurve-probe/v1",
        "authority": "early_indicator_only_full_audit_required",
        "result_count": result["result_count"],
        "status_counts": result["status_counts"],
        "unique_face_count": result["unique_face_count"],
        "unique_edge_count": result["unique_edge_count"],
        "private_mapping": {
            "face_edge_pairs_private": result["face_edge_pairs_private"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result_count": report["result_count"],
                "status_counts": report["status_counts"],
                "unique_face_count": report["unique_face_count"],
                "unique_edge_count": report["unique_edge_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["result_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
