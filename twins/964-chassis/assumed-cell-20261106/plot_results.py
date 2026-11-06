#!/usr/bin/env python3
"""Plot actual conditional tangent-stiffness results, never vehicle allowables."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--results", type=Path, default=HERE / "linear-results.json")
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
if args.output.exists():
    ap.error("Use a fresh plot output path.")
data = json.loads(args.results.read_text())
variants = ["baseline", "tunnel-low", "tunnel-high", "open-tunnel", "wall-thin", "wall-thick"]
names = ["Baseline", "Tunnel\n160 mm", "Tunnel\n280 mm", "Tunnel\nomitted", "Wall\n2 mm", "Wall\n4 mm"]
values = []
for variant in variants:
    rows = {r["case"]: r for r in data["results"]
            if r["variant"] == variant and r["h_mm"] == 80 and r["load_factor"] == 1}
    assert set(rows) == {"torsion", "bending"}
    values.append((rows["torsion"]["nominal_shell_mass_kg"],
                   rows["torsion"]["metrics"]["torsion_stiffness_Nm_per_deg"],
                   rows["bending"]["metrics"]["bending_stiffness_N_per_mm"]))
fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle("Assumed central-tub sensitivity | actual layered-shell runs", fontsize=17)
colors = ["#285a71"] + ["#8299a4"] * 5
for index, (ax, title, unit) in enumerate(zip(axes,
        ["Nominal shell mass", "Linear tangent torsion stiffness", "Linear tangent floor-fixture stiffness"],
        ["kg, excludes joints / inserts / upper structure", "N m / degree", "N / mm"])):
    y = [v[index] for v in values]
    ax.bar(names, y, color=colors)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(unit, fontsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_ylim(0, max(y) * 1.17)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    for x, value in enumerate(y):
        ax.text(x, value + max(y) * 0.025, f"{value:,.1f}" if index == 0 else f"{value:,.0f}",
                ha="center", fontsize=8)
fig.text(0.5, 0.025,
         "h = 80 mm parameter; front-end clamp; assumed carbon/epoxy and perfectly continuous joints.\n"
         "Tangent comparisons only: finite-load geometric nonlinearity is checked separately. No measured fit, strength or manufacturing approval.",
         ha="center", fontsize=10)
fig.tight_layout(rect=(0.01, 0.13, 0.99, 0.92))
args.output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.output, dpi=120)
plt.close(fig)
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt = dict(classification="actual_assumed_linear_stiffness_comparison_plot",
               results_sha256=hashfile(args.results), source_sha256=hashfile(Path(__file__)),
               image_sha256=hashfile(args.output), matplotlib_version=matplotlib.__version__,
               variants=variants, numerical_data_invented=False, physical_validation=False)
args.output.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
