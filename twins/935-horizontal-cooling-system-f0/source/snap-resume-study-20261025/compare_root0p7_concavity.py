"""Compare native concave-cell topology in two rejected corrected-rotor meshes."""

import json
from pathlib import Path
import sys

import numpy as np

from compare_root0p7_spacing import read_case
from localize_concave_cells import digest, read_label_list, read_set, rotor_graph_layers


def audit(case: Path, spacing: int) -> dict:
    verified = read_case(case, spacing)
    mesh = case / "constant/polyMesh"
    levels = read_label_list(mesh / "cellLevel")
    bad_ids = read_set(mesh / "sets/concaveCells")
    if len(levels) != verified["cell_count"] or len(bad_ids) != verified["concave_cells"]:
        raise ValueError("Native cell list or concave set disagrees with full checkMesh")
    bad = np.zeros(len(levels), dtype=bool)
    bad[bad_ids] = True
    owner = read_label_list(mesh / "owner")
    neighbour = read_label_list(mesh / "neighbour")
    internal_owner = owner[:len(neighbour)]
    if (len(neighbour) >= len(owner) or owner.min() < 0 or neighbour.min() < 0
            or owner.max() >= len(levels) or neighbour.max() >= len(levels)):
        raise ValueError("Invalid native face ownership")
    jumps = np.abs(levels[internal_owner] - levels[neighbour])
    if jumps.max() > 1:
        raise ValueError("Unexpected refinement jump")
    crossing = jumps != 0
    adjacent = np.zeros(len(levels), dtype=bool)
    adjacent[internal_owner[crossing]] = True
    adjacent[neighbour[crossing]] = True

    def counts(mask: np.ndarray) -> dict:
        total = int(np.count_nonzero(mask))
        failures = int(np.count_nonzero(mask & bad))
        return {"cells": total, "concave_cells": failures,
                "concave_fraction": failures / total if total else None}

    by_level = []
    for level in np.unique(levels):
        current = levels == level
        by_level.append({"level": int(level), "all": counts(current),
                         "transition_adjacent": counts(current & adjacent),
                         "other": counts(current & ~adjacent)})
    by_transition_pair = []
    for lower in range(int(levels.max())):
        pair_faces = ((levels[internal_owner] == lower) & (levels[neighbour] == lower + 1)
                      | (levels[internal_owner] == lower + 1) & (levels[neighbour] == lower))
        pair_cells = np.zeros(len(levels), dtype=bool)
        pair_cells[internal_owner[pair_faces]] = True
        pair_cells[neighbour[pair_faces]] = True
        by_transition_pair.append({"levels": [lower, lower + 1],
                                   "internal_faces": int(np.count_nonzero(pair_faces)),
                                   "lower_side": counts(pair_cells & (levels == lower)),
                                   "higher_side": counts(pair_cells & (levels == lower + 1))})
    result = {"spacing": spacing,
              "case": str(case),
              "rotor_obj_sha256": verified["rotor_obj_sha256"],
              "cell_count": len(levels), "concave_cell_count": len(bad_ids),
              "cell_level_sha256": digest(mesh / "cellLevel"),
              "concave_set_sha256": digest(mesh / "sets/concaveCells"),
              "owner_sha256": digest(mesh / "owner"),
              "neighbour_sha256": digest(mesh / "neighbour"),
              "transition_internal_faces": int(np.count_nonzero(crossing)),
              "transition_adjacent": counts(adjacent),
              "other": counts(~adjacent),
              "by_level": by_level,
              "by_transition_pair": by_transition_pair,
              "rotor_wall_graph_layers": rotor_graph_layers(case, len(levels), bad_ids),
              "native_quality_passed": False, "CFD_accepted": False}
    if (result["transition_adjacent"]["cells"] + result["other"]["cells"] != len(levels)
            or result["transition_adjacent"]["concave_cells"] + result["other"]["concave_cells"] != len(bad_ids)
            or sum(row["all"]["cells"] for row in by_level) != len(levels)):
        raise ValueError("Cross-tab does not account for every cell")
    return result


def run(case3: Path, case5: Path, output: Path) -> None:
    case3, case5, output = case3.resolve(), case5.resolve(), output.resolve()
    if output.exists() or case3.parent != case5.parent or output.parent != case3.parent:
        raise ValueError("Use two sibling native cases and a fresh private sibling output")
    rows = [audit(case3, 3), audit(case5, 5)]
    if rows[0]["rotor_obj_sha256"] != rows[1]["rotor_obj_sha256"]:
        raise ValueError("Corrected rotor differs between cases")
    report = {"status": "rejected_corrected_rotor_concavity_topology_not_CFD_admitted",
              "analysis_source_sha256": digest(Path(__file__)),
              "cases": rows,
              "source_unit_to_mm_verified": False,
              "mesh_quality_passed": False,
              "CFD_executed": False, "CFD_accepted": False,
              "manufacturing_authorized": False}
    output.mkdir(mode=0o700)
    path = output / "concavity-topology.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    names = ["spacing 3", "spacing 5"]
    for axis, key, title in ((axes[0], "transition_adjacent", "Adjacent to level change"),
                             (axes[1], "other", "No adjacent level change")):
        axis.bar(names, [100 * row[key]["concave_fraction"] for row in rows])
        axis.set(ylabel="Concave cells (%)", title=title)
    pairs = ["0/1", "1/2", "2/3", "3/4"]
    x = np.arange(len(pairs))
    for offset, row, label in ((-.18, rows[0], names[0]), (.18, rows[1], names[1])):
        axes[2].bar(x + offset,
                    [item["lower_side"]["concave_cells"] for item in row["by_transition_pair"]],
                    width=.35, label=label)
    axes[2].set(xticks=x, xticklabels=pairs, xlabel="Adjacent refinement levels",
                ylabel="Concave cells on lower side", title="Transition-pair location")
    axes[2].legend()
    fig.suptitle("935 corrected rotor: both native meshes rejected")
    fig.tight_layout()
    image = output / "concavity-topology.png"
    fig.savefig(image, dpi=170)
    plt.close(fig)
    path.chmod(0o600)
    image.chmod(0o600)
    print(json.dumps({"status": report["status"],
                      "cases": [{"spacing": row["spacing"],
                                 "transition_adjacent": row["transition_adjacent"],
                                 "other": row["other"]} for row in rows],
                      "report_sha256": digest(path), "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: compare_root0p7_concavity.py SPACING3_CASE SPACING5_CASE NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
