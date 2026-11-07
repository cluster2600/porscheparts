"""Plot the published H10 geometry receipt; no mechanical response is inferred."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "h10-expanded-geometry.json"
OUTPUT = ROOT.parents[1] / "media/carrier-h10-geometry-20261107.png"
data = json.loads(SOURCE.read_text())
assert data["status"] == "expanded_H10_selection_and_complete_two_frame_geometry_passed"
assert data["map"]["full_array_identity"] and data["map"]["returncode"] == 0
assert not data["scope"]["H10_response_executed"] and not data["scope"]["convergence_claimed"]
geometry, selection = data["geometry"], data["selection"]
assert geometry["vertices"] == data["map"]["new_vertices"] == 5039930
assert geometry["cells"] == data["map"]["new_cells"] == 20083501
assert geometry["new_children"] == 2 * selection["split_source_cells"]
values = [100 * selection["case_coverage"][case]["coverage"] for case in ("gravity", "combined")]
assert all(50 <= value <= 100 for value in values)
assert not OUTPUT.exists(), "Preserve existing image evidence"

fig, axes = plt.subplots(1, 2, figsize=(12, 5.3), layout="constrained", facecolor="#f3f6fa")
ax = axes[0]
bars = ax.bar(["Gravity", "Combined"], values, width=.55, color=["#117f91", "#487191"])
ax.axhline(50, color="#b15d2d", linestyle="--", linewidth=1.5, label="50% selection target per load")
ax.bar_label(bars, labels=[f"{v:.6f}%" for v in values], padding=7, fontsize=12, weight="bold")
ax.set(ylabel="Selected source indicator [%]", ylim=(0, 65), title="Both selection targets reached")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=.15)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax = axes[1]
ax.axis("off")
ax.text(.02, .96, "Complete geometry and nesting checked", fontsize=13, weight="bold", color="#17334b", va="top")
rows = [("Vertices", f"{geometry['vertices']:,}"), ("Tetrahedra", f"{geometry['cells']:,}"),
        ("New children checked in both frames", f"{geometry['new_children']:,}"),
        ("Selected non-midpoint edge points", f"{selection['exact_nonmidpoint_stars']:,}"),
        ("Inherited protected cells unchanged", str(geometry['protected_cells_unchanged'])),
        ("New cells at or above 1e6 condition", str(geometry['new_extreme_cells']))]
for index, (label, value) in enumerate(rows):
    y = .79 - index * .105
    ax.text(.02, y, label, fontsize=10, color="#34495e")
    ax.text(.98, y, value, ha="right", fontsize=11, weight="bold", color="#117f91")
ax.text(.02, .08, "Maximum new-cell condition: 999,997.6266\nClose to the unchanged 1,000,000 limit", fontsize=9, color="#8b512d")
fig.suptitle("993 Turbo carrier | H10 refinement geometry", fontsize=18, weight="bold", color="#17334b")
fig.supxlabel("Selection coverage is not a convergence error. Original exterior, loads and support nodes retained.\nH10 native responses and complete energy-norm comparison remain pending. No mass ceiling.", fontsize=9, color="#34495e")
fig.savefig(OUTPUT, dpi=150)
plt.close(fig)
receipt = dict(status="published_H10_geometry_scalars_plotted_mechanical_response_pending",
               source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               image_sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
               selection_percent=values, mechanical_response=False, convergence_claimed=False)
with (ROOT / "h10-figure-provenance.json").open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(OUTPUT)
