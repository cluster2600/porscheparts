"""Compare pinned native cfMesh 935 volumes at two rotor-local resolutions."""

import json
from pathlib import Path
import sys

from audit_cfmesh_sweep import CASES, audit_case


FINE_MESHDICT_SHA = "d8ed88bf0a58e54de54396762b8d68d7f8864e06f49b1057d552af68358d2431"


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: audit_cfmesh_resolution.py CASE_PARENT_DIR NEW_REPORT_JSON")
    root, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if output.exists():
        raise SystemExit("Use a fresh report path")
    source_sha, rotor_faces = CASES["case-001"]
    coarse = audit_case(root / "case-001", source_sha, rotor_faces)
    fine = audit_case(root / "case-005", source_sha, rotor_faces, FINE_MESHDICT_SHA)
    if coarse["failed_mesh_checks"] != 8 or fine["failed_mesh_checks"] != 8:
        raise ValueError("Unexpected quality outcome")
    report = {
        "status": "finer_rotor_local_cfmesh_rejected_for_CFD",
        "source_to_SI_scale_verified": False,
        "same_rotor_and_outer_surface_sha256": source_sha,
        "same_quality_dictionary_sha256": coarse["meshQualityDict_sha256"],
        "coarse": coarse,
        "fine": fine,
        "fine_minus_coarse": {name: fine[name] - coarse[name] for name in
                              ("cells", "faces", "severely_nonorthogonal_faces",
                               "highly_skew_faces", "low_quality_face_tets",
                               "small_determinant_cells", "concave_cells",
                               "low_weight_faces", "low_volume_ratio_faces")},
        "CFD_admitted": False,
        "manufacturing_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "deltas": report["fine_minus_coarse"]}))


if __name__ == "__main__":
    main()
