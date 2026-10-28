"""Audit the four pinned, private cfMesh 935 fluid-volume cases."""

import hashlib
import json
from pathlib import Path
import re
import sys


CASES = {
    "case-001": ("5982ea677297537ec3dfff9825a70a3665b534666751050889a8f567ff4a7ffb", 878730),
    "case-002": ("bae46ddb0cb9badb2d1e3f01ff689f788bc2fb4c41fa46af1499e516cafd2638", 878716),
    "case-003": ("c32492dda2554133cbf9a551f2992ed2ee0631152f79685ae059ee54870e14f9", 878646),
    "case-004": ("47dcb04eeb893d6a8f1c687d170f3ab214ec284ef2f170fbad713622a222acac", 878698),
}
MESHDICT_SHA = "736d74e38e28371841a2004f97221a3bec5e04f54fd8507bb1d1be7dc7c7c6a1"
QUALITY_SHA = "bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d"


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def match_int(pattern, content):
    found = re.search(pattern, content, re.MULTILINE)
    if not found:
        raise ValueError(f"Missing native quality metric: {pattern}")
    return int(found.group(1))


def audit_case(path, expected_stl, expected_rotor_faces, mesh_dict_sha=MESHDICT_SHA):
    mesh_dict = path / "system/meshDict"
    quality_dict = path / "system/meshQualityDict"
    stl = path / "constant/triSurface/boundary.stl"
    if digest(mesh_dict) != mesh_dict_sha or digest(quality_dict) != QUALITY_SHA:
        raise ValueError(f"Different meshing/quality dictionary in {path.name}")
    if digest(stl) != expected_stl:
        raise ValueError(f"Different fluid PLC in {path.name}")
    surface = (path / "log.surfaceCheck").read_text()
    for patch, count in (("inlet", 2304), ("outlet", 2304), ("duct", 12394),
                         ("rotor", expected_rotor_faces)):
        if not re.search(rf"^{patch}\s+{count}$", surface, re.MULTILINE):
            raise ValueError(f"Surface patch mismatch: {path.name}/{patch}")
    if "Surface is closed. All edges connected to two faces." not in surface or "Surface has no illegal triangles." not in surface:
        raise ValueError(f"Input surface not admitted: {path.name}")
    mesher = (path / "log.cartesianMesh").read_text()
    if not mesher.rstrip().endswith("End") or "Finished renaming boundary patches" not in mesher:
        raise ValueError(f"Mesher did not finish: {path.name}")
    quality_path = path / ("log.checkMesh.full" if path.name == "case-001" else "log.checkMesh")
    quality = quality_path.read_text()
    if not quality.rstrip().endswith("End"):
        raise ValueError(f"Full checkMesh did not finish: {path.name}")
    result = {
        "stl_sha256": expected_stl,
        "meshDict_sha256": mesh_dict_sha,
        "meshQualityDict_sha256": QUALITY_SHA,
        "rotor_input_triangles": expected_rotor_faces,
        "points": match_int(r"^\s+points:\s+(\d+)$", quality),
        "faces": match_int(r"^\s+faces:\s+(\d+)$", quality),
        "cells": match_int(r"^\s+cells:\s+(\d+)$", quality),
        "boundary_patches": match_int(r"^\s+boundary patches:\s+(\d+)$", quality),
        "failed_mesh_checks": match_int(r"^Failed (\d+) mesh checks\.$", quality),
        "high_aspect_ratio_cells": match_int(r"High aspect ratio cells found, Max aspect ratio: [0-9.eE+-]+, number of cells (\d+)", quality),
        "severely_nonorthogonal_faces": match_int(r"Number of severely non-orthogonal \(> 70 degrees\) faces: (\d+)", quality),
        "highly_skew_faces": match_int(r"Max skewness = [0-9.eE+-]+, (\d+) highly skew faces", quality),
        "low_quality_face_tets": match_int(r"Error in face tets: (\d+) faces", quality),
        "small_determinant_cells": match_int(r"Cells with small determinant \(< 0\.001\) found, number of cells: (\d+)", quality),
        "concave_cells": match_int(r"Concave cells \(using face planes\) found, number of cells: (\d+)", quality),
        "low_weight_faces": match_int(r"Faces with small interpolation weight \(< 0\.05\) found, number of faces: (\d+)", quality),
        "low_volume_ratio_faces": match_int(r"Faces with small volume ratio \(< 0\.01\) found, number of faces: (\d+)", quality),
    }
    if result["boundary_patches"] != 4 or result["failed_mesh_checks"] < 1:
        raise ValueError(f"Unexpected quality status in {path.name}")
    result["CFD_admitted"] = False
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: audit_cfmesh_sweep.py CASE_PARENT_DIR NEW_REPORT_JSON")
    root, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if output.exists():
        raise SystemExit("Use a fresh report path")
    report = {
        "status": "four_cfmesh_cases_rejected_for_CFD",
        "source_to_SI_scale_verified": False,
        "cases": {case: audit_case(root / case, *values) for case, values in CASES.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({case: {key: row[key] for key in ("cells", "failed_mesh_checks", "concave_cells")}
                      for case, row in report["cases"].items()}))


if __name__ == "__main__":
    main()
