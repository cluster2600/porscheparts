#!/usr/bin/env python3
"""Apply the existing unmodified raw-triangle inspector to F16 exports."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct

import numpy as np
import trimesh

from run_leap_f16 import ROOT, verify_output, sha256


def inspect(directory):
    native = verify_output(directory)
    source = ROOT / "twins/bionic-turbo-f0/inspect_mesh.py"
    spec = importlib.util.spec_from_file_location("raw_inspector", source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rows = []
    for part in native["components"]:
        path = directory / part["stl"]
        with path.open("rb") as stream:
            count = struct.unpack_from("<I", stream.read(84), 80)[0]
        if path.stat().st_size != 84 + 50 * count or count != part["triangles"]:
            raise ValueError("Raw STL count mismatch")
        raw = trimesh.load_mesh(path, file_type="stl", process=False)
        if len(raw.faces) != count:
            raise ValueError("Loader changed the raw triangle count")
        result, _ = module.inspect_triangles(raw.triangles)
        rows.append({"id": part["id"], "sha256": sha256(path), **result})
    report = {"status": "passed_raw_mesh_screen" if all(r["passed"] for r in rows) else "failed_raw_mesh_screen",
              "native_report_sha256": sha256(directory / "report.json"), "inspector_sha256": sha256(source),
              "adapter_sha256": sha256(Path(__file__)), "numpy": np.__version__, "trimesh": trimesh.__version__,
              "mesh_modified": False, "self_intersections_checked": False,
              "manufacturing_authorized": False, "components": rows}
    path = directory / "raw-mesh-inspection.json"
    if path.exists(): raise ValueError("Retain the previous inspection")
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "failures": {r["id"]: r["failures"] for r in rows if not r["passed"]}}, indent=2))
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    raise SystemExit(inspect(parser.parse_args().directory.resolve()))
