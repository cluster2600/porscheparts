"""Compare two rejected native meshes of the same corrected PicoGK 935 rotor."""

import json
from pathlib import Path
import re
import sys

import numpy as np

from localize_concave_cells import digest, read_label_list


def read_case(path: Path, expected_spacing: int) -> dict:
    prep = json.loads((path / "preparation.json").read_text())
    execution = json.loads((path / "execution.json").read_text())
    check = json.loads((path / "quality-check.json").read_text())
    snappy = (path / "system/snappyHexMeshDict").read_text()
    log = (path / "log.checkMesh.full").read_text()
    if (execution["exit"] != 0 or execution["status"] != "snappy_finished"
            or check["exit"] != 0 or check["status"] != "native_quality_rejected_or_incomplete"
            or "Finished meshing without any errors" not in (path / "log.snappyHexMesh").read_text()
            or "Failed 1 mesh checks." not in log or "Mesh OK." in log
            or snappy.count(f"nCellsBetweenLevels {expected_spacing};") != 1
            or digest(path / "system/snappyHexMeshDict") != prep["trial_snappy_dict_sha256"]
            or digest(path / "system/meshQualityDict") != prep["quality_dict_sha256"]
            or digest(path / "constant/triSurface/rotor.obj") != prep["source_rotor_obj_sha256"]
            or execution["source_rotor_unchanged"] is not True
            or execution["mesh_quality_dict_unchanged"] is not True):
        raise ValueError("Unverified native trial or accepted mesh supplied")
    cell_match = re.search(r"^\s+cells:\s+(\d+)\s*$", log, re.MULTILINE)
    bad_match = re.search(r"Concave cells .*number of cells: (\d+)", log)
    if not cell_match or not bad_match:
        raise ValueError("Native cell counts missing")
    cells, bad = int(cell_match.group(1)), int(bad_match.group(1))
    levels = read_label_list(path / "constant/polyMesh/cellLevel")
    owner = read_label_list(path / "constant/polyMesh/owner")
    boundary = (path / "constant/polyMesh/boundary").read_text()
    rotor = re.search(r"\brotor\s*\{([^{}]*)\}", boundary, re.DOTALL)
    if not rotor:
        raise ValueError("Rotor patch missing")
    n_faces = re.search(r"\bnFaces\s+(\d+)\s*;", rotor.group(1))
    start = re.search(r"\bstartFace\s+(\d+)\s*;", rotor.group(1))
    if not n_faces or not start or len(levels) != cells:
        raise ValueError("Native rotor or cell level count mismatch")
    n_faces, start = int(n_faces.group(1)), int(start.group(1))
    if start + n_faces > len(owner) or owner.min() < 0 or owner.max() >= cells:
        raise ValueError("Invalid rotor face ownership")
    wall_levels = levels[owner[start:start + n_faces]]
    return {"case": str(path), "spacing": expected_spacing,
            "rotor_obj_sha256": prep["source_rotor_obj_sha256"],
            "quality_dict_sha256": prep["quality_dict_sha256"],
            "snappy_dict_sha256": prep["trial_snappy_dict_sha256"],
            "snappy_dict_normalized": snappy.replace(f"nCellsBetweenLevels {expected_spacing};",
                                                      "nCellsBetweenLevels X;"),
            "snappy_log_sha256": execution["log_snappy_sha256"],
            "check_mesh_log_sha256": check["log_sha256"],
            "cell_level_sha256": digest(path / "constant/polyMesh/cellLevel"),
            "cell_count": cells, "concave_cells": bad,
            "concave_fraction": bad / cells,
            "rotor_patch_faces": n_faces,
            "rotor_patch_cell_levels": {str(int(v)): int(c) for v, c in zip(*np.unique(wall_levels, return_counts=True))},
            "snappy_elapsed_s": execution["elapsed_s"],
            "quality_status": check["status"],
            "duplicate_face_warning_present": "duplicate (not baffle) faces found" in log,
            "cell_cap_reached_in_log": "No cells marked for refinement since reached limit" in (path / "log.snappyHexMesh").read_text()}


def run(first: Path, second: Path, output: Path) -> None:
    first, second, output = first.resolve(), second.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(first.parent) or second.parent != first.parent:
        raise ValueError("Use two sibling cases and a fresh private sibling output")
    a, b = read_case(first, 3), read_case(second, 5)
    if (a["rotor_obj_sha256"] != b["rotor_obj_sha256"]
            or a["quality_dict_sha256"] != b["quality_dict_sha256"]
            or a.pop("snappy_dict_normalized") != b.pop("snappy_dict_normalized")):
        raise ValueError("Trial inputs differ beyond spacing")
    report = {"status": "matched_rejected_mesh_pair_no_CFD_admission",
              "analysis_source_sha256": digest(Path(__file__)),
              "cases": [a, b],
              "source_unit_to_mm_verified": False,
              "spacing_isolated_in_input": True,
              "wall_fidelity_to_scan_verified": False,
              "both_quality_passed": False,
              "CFD_executed": False,
              "CFD_accepted": False,
              "manufacturing_authorized": False}
    output.mkdir(mode=0o700)
    result = output / "spacing-comparison.json"
    result.write_text(json.dumps(report, indent=2) + "\n")
    result.chmod(0o600)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    names = ["spacing 3", "spacing 5"]
    axes[0].bar(names, [r["cell_count"] for r in (a, b)])
    axes[0].set(ylabel="Cells", title="Final cell count")
    axes[1].bar(names, [100 * r["concave_fraction"] for r in (a, b)], color="#ca5c42")
    axes[1].set(ylabel="Concave cells (%)", title="Rejected-cell rate")
    levels = sorted({int(level) for row in (a, b) for level in row["rotor_patch_cell_levels"]})
    x = np.arange(len(levels))
    for offset, row, label in ((-.18, a, names[0]), (.18, b, names[1])):
        axes[2].bar(x + offset, [row["rotor_patch_cell_levels"].get(str(level), 0)
                                 for level in levels], width=.35, label=label)
    axes[2].set(xticks=x, xticklabels=levels, xlabel="Native cell level at rotor wall",
                ylabel="Patch faces", title="Wall refinement")
    axes[2].legend()
    fig.suptitle("935 corrected rotor: both meshes rejected; scan fidelity unverified")
    fig.tight_layout()
    image = output / "spacing-comparison.png"
    fig.savefig(image, dpi=170)
    plt.close(fig)
    image.chmod(0o600)
    print(json.dumps({"status": report["status"],
                      "cases": [{k: row[k] for k in ("spacing", "cell_count", "concave_cells",
                                                         "concave_fraction", "rotor_patch_faces",
                                                         "rotor_patch_cell_levels", "cell_cap_reached_in_log")}
                                for row in (a, b)],
                      "report_sha256": digest(result), "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compare_root0p7_spacing.py SPACING3_CASE SPACING5_CASE NEW_PRIVATE_OUTPUT")
    run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
