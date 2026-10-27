"""Test whether rejected 935 cells cluster at native refinement transitions."""

import json
from pathlib import Path
import sys

import numpy as np

from localize_concave_cells import QUALITY_SHA256, SOURCE_KEYS, digest, read_label_list, read_set


def run(case: Path, output: Path) -> None:
    case, output = case.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(case.parent):
        raise ValueError("Use a fresh private output beside the copied case")
    execution = json.loads((case / "execution.json").read_text())
    if (execution["status"] != "diagnostic_only_rejected_mesh"
            or execution["CFD_accepted"] or execution["timeout"]
            or execution["copied_input_sha256"]["system/meshQualityDict"] != QUALITY_SHA256
            or set(execution["copied_input_sha256"]) != set(SOURCE_KEYS)):
        raise ValueError("Input is not the pinned rejected case")
    if any(digest(case / key) != execution["copied_input_sha256"][key] for key in SOURCE_KEYS):
        raise ValueError("Copied native mesh changed")
    mesh = case / "constant/polyMesh"
    levels = read_label_list(mesh / "cellLevel")
    if len(levels) != 4_666_166 or levels.min() < 0:
        raise ValueError("Unexpected native cellLevel field")
    rejected_ids = read_set(mesh / "sets/concaveCells")
    if len(rejected_ids) != 316_996 or rejected_ids.min() < 0 or rejected_ids.max() >= len(levels):
        raise ValueError("Unexpected native concaveCells set")
    rejected = np.zeros(len(levels), dtype=bool)
    rejected[rejected_ids] = True
    owner, neighbour = read_label_list(mesh / "owner"), read_label_list(mesh / "neighbour")
    if len(owner) != 15_223_252 or len(neighbour) >= len(owner):
        raise ValueError("Unexpected native face counts")
    own_internal = owner[:len(neighbour)]
    if owner.min() < 0 or owner.max() >= len(levels) or neighbour.min() < 0 or neighbour.max() >= len(levels):
        raise ValueError("Invalid native owner/neighbour")
    delta = np.abs(levels[own_internal] - levels[neighbour])
    if delta.max() > 1:
        raise ValueError("Refinement jump exceeds one level")
    transition_faces = delta != 0
    adjacent = np.zeros(len(levels), dtype=bool)
    adjacent[own_internal[transition_faces]] = True
    adjacent[neighbour[transition_faces]] = True

    def counts(mask: np.ndarray) -> dict:
        total = int(np.count_nonzero(mask))
        bad = int(np.count_nonzero(mask & rejected))
        return {"cells": total, "concave_cells": bad,
                "concave_fraction": bad / total if total else None}

    by_level = []
    for level in np.unique(levels):
        mask = levels == level
        by_level.append({"level": int(level), "all": counts(mask),
                         "transition_adjacent": counts(mask & adjacent),
                         "not_transition_adjacent": counts(mask & ~adjacent)})
    report = {
        "status": "rejected_mesh_refinement_correlation_not_CFD_admitted",
        "analysis_source_sha256": digest(Path(__file__)),
        "copied_case": str(case),
        "quality_dictionary_sha256": QUALITY_SHA256,
        "copied_input_sha256": execution["copied_input_sha256"],
        "cell_level_sha256": digest(mesh / "cellLevel"),
        "concave_set_sha256": digest(mesh / "sets/concaveCells"),
        "cell_count": len(levels),
        "concave_cell_count": len(rejected_ids),
        "internal_face_count": len(neighbour),
        "transition_internal_face_count": int(np.count_nonzero(transition_faces)),
        "transition_adjacent": counts(adjacent),
        "not_transition_adjacent": counts(~adjacent),
        "by_level": by_level,
        "correlation_is_causality": False,
        "mesh_quality_passed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    if sum(row["all"]["cells"] for row in by_level) != len(levels):
        raise ValueError("Cell levels do not partition the mesh")
    if report["transition_adjacent"]["concave_cells"] + report["not_transition_adjacent"]["concave_cells"] != len(rejected_ids):
        raise ValueError("Concave-cell accounting failed")
    output.mkdir(mode=0o700)
    path = output / "refinement-correlation.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    path.chmod(0o600)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    names = ["Adjacent to level change", "No adjacent level change"]
    rates = [100 * report[key]["concave_fraction"] for key in
             ("transition_adjacent", "not_transition_adjacent")]
    axes[0].bar(names, rates, color=["#d66540", "#337d8c"])
    axes[0].set(ylabel="Concave cells (%)", title="Conditional rate by refinement transition")
    axes[0].tick_params(axis="x", labelrotation=15)
    level_names = [str(row["level"]) for row in by_level]
    axes[1].bar(level_names, [row["transition_adjacent"]["concave_cells"] for row in by_level],
                label="Adjacent to level change", color="#d66540")
    axes[1].bar(level_names, [row["not_transition_adjacent"]["concave_cells"] for row in by_level],
                bottom=[row["transition_adjacent"]["concave_cells"] for row in by_level],
                label="Other", color="#337d8c")
    axes[1].set(xlabel="Native cell refinement level", ylabel="Concave cells",
                title="Rejected cells by level")
    axes[1].set_ylim(0, 1.15 * max(row["all"]["concave_cells"] for row in by_level))
    axes[1].legend()
    fig.suptitle("935 rejected CFD mesh: correlation, not causal proof")
    fig.tight_layout()
    image = output / "refinement-correlation.png"
    fig.savefig(image, dpi=170)
    plt.close(fig)
    image.chmod(0o600)
    print(json.dumps({"status": report["status"],
                      "transition_adjacent": report["transition_adjacent"],
                      "not_transition_adjacent": report["not_transition_adjacent"],
                      "report_sha256": digest(path), "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: correlate_concavity_refinement.py COPIED_NATIVE_CASE NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
