"""Compare a pinned, rejected splitCells trial with its native parent mesh."""

import json
from pathlib import Path
import re
import sys
import tarfile

from compare_smooth_patch import (
    PARENT_SHA256, QUALITY_SHA256, ROTOR_SHA256, digest, member_digest,
    member_text, metrics,
)


CHILD_SHA256 = "beeb96ef0cd472c4eda07c094cf6952a1575a372162fa8a22f56c1c85243f40f"
PARENT = "snappy-refine34-spaced3-20261028"
CHILD = "split180-case"


def run(parent_path, child_path, output):
    parent_path, child_path, output = (path.resolve() for path in
                                       (parent_path, child_path, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report path")
    if digest(parent_path) != PARENT_SHA256 or digest(child_path) != CHILD_SHA256:
        raise ValueError("Pinned native archive changed")
    with tarfile.open(parent_path, "r:gz") as parent, tarfile.open(child_path, "r:gz") as child:
        common = ("system/blockMeshDict", "system/controlDict", "system/fvSchemes",
                  "system/fvSolution", "system/meshQualityDict",
                  "system/snappyHexMeshDict", "constant/triSurface/rotor.obj")
        common_hashes = {}
        for name in common:
            old = member_digest(parent, f"{PARENT}/{name}")
            new = member_digest(child, f"{CHILD}/{name}")
            if old != new:
                raise ValueError(f"Native input changed: {name}")
            common_hashes[name] = old
        if (common_hashes["system/meshQualityDict"] != QUALITY_SHA256
                or common_hashes["constant/triSurface/rotor.obj"] != ROTOR_SHA256):
            raise ValueError("Corrected rotor or quality baseline changed")
        if (member_digest(parent, f"{PARENT}/log.checkMesh.full")
                != member_digest(child, f"{CHILD}/log.checkMesh.full")):
            raise ValueError("Copied parent quality log changed")
        before = metrics(member_text(parent, f"{PARENT}/log.checkMesh.full"))
        after_log = member_text(child, f"{CHILD}/log.checkMesh.afterSplit")
        after = metrics(after_log)
        split_log = member_text(child, f"{CHILD}/log.splitCells")
        script = member_text(child, "run_split.sh")
        if (split_log.count('candidate cells   : cellSet "concaveCells"') != 1
                or split_log.count("featureAngle      : 180") != 1
                or "splitCells -case /workspace -set concaveCells 180" not in script):
            raise ValueError("Native splitCells selection changed")
        cuts = [int(value) for value in re.findall(r"^Actually cut cells:(\d+)\s*$",
                                                   split_log, re.MULTILINE)]
        if not cuts or cuts[-1] != 0 or sum(cuts) != after["cells"] - before["cells"]:
            raise ValueError("Native split count disagrees with checkMesh")
        failures = re.findall(r"^ \*\*\*(.+)$", after_log, re.MULTILINE)
    if before["failed_mesh_checks"] != 1 or after["failed_mesh_checks"] != 9:
        raise ValueError("Unexpected native quality outcome")
    report = {
        "status": "rejected_splitCells_180_no_CFD",
        "archive_sha256": {"parent": PARENT_SHA256, "child": CHILD_SHA256},
        "common_input_sha256": common_hashes,
        "selection": {"cell_set": "concaveCells", "internal_angle_degrees": 180,
                      "cut_cells_per_pass": cuts, "total_cut_cells": sum(cuts)},
        "checkMesh": {"before": before, "after": after},
        "after_failed_diagnostic_lines": failures,
        "new_concave_cells": after["concave_cells"] - before["concave_cells"],
        "source_unit_to_mm_verified": False,
        "full_checkMesh_passed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({"status": report["status"], "report_sha256": digest(output),
                      "new_concave_cells": report["new_concave_cells"]}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compare_split_cells.py PARENT_ARCHIVE CHILD_ARCHIVE NEW_PRIVATE_REPORT")
    run(*(Path(value) for value in sys.argv[1:]))
