#!/usr/bin/env python3
"""Render computed WE43 bulk temperatures and numerical sensitivities, never a melt pool."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np


def render(cases, output):
    reports = [json.loads((case / "summary.json").read_text()) for case in cases]
    reference = reports[0]
    if any(report["hashes"]["surface"] != reference["hashes"]["surface"]
           or report["hashes"]["card"] != reference["hashes"]["card"]
           or report["status"] != "transient_3d_bulk_thermal_solve_completed"
           or report["manufacturing_authorized"] for report in reports):
        raise ValueError("Inconsistent or inadmissible thermal cases")
    for case, report in zip(cases, reports):
        if any(hashlib.sha256((case / name).read_bytes()).hexdigest() != report["output_hashes"][name]
               for name in ("thermal-fields.npz", "history.json")):
            raise ValueError("Thermal field or history digest mismatch")
    fields = np.load(cases[0] / "thermal-fields.npz", allow_pickle=False)
    mask = fields["is_part"]
    centres = fields["centres_mm"][mask]
    peak, cooled = fields["peak_k"][mask], fields["cooled_k"][mask]
    if not np.isfinite(centres).all() or not np.isfinite(peak).all() or not np.isfinite(cooled).all():
        raise ValueError("Nonfinite physical fields")
    output.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 10), dpi=120)
    exceeded = any(report["cp_reference_temperature_range_exceeded"] for report in reports)
    orientation = {"build_z": "flat", "roll_y_45": "45° tilt"}[reference["orientation"]]
    fig.suptitle(f"WE43 impeller — {orientation}, transient thermal diagnostic" +
                 ("\nMaterial reference range exceeded — temperatures not validated" if exceeded else ""), fontsize=14)
    stride = max(1, len(centres) // 12000)
    points = centres[::stride]
    for index, values, title in ((1, peak, "Maximum bulk temperature during build"),
                                 (2, cooled, "After 120 s cooldown")):
        ax = fig.add_subplot(2, 2, index, projection="3d")
        dots = ax.scatter(*points.T, c=values[::stride] - 273.15, cmap="inferno", s=4,
                          vmin=min(peak.min(), cooled.min()) - 273.15, vmax=min(100., peak.max() - 273.15))
        ax.set_title(title)
        ax.set_box_aspect(np.ptp(centres, axis=0))
        ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)"); ax.set_zlabel("Z (mm)")
        ax.zaxis.set_major_locator(MaxNLocator(3))
        fig.colorbar(dots, ax=ax, shrink=.65, pad=.16, label="°C (values >100 above scale)" if peak.max() > 373.15 else "°C",
                     extend="max" if peak.max() > 373.15 else "neither")
    ax = fig.add_subplot(2, 2, 3)
    for case, report in zip(cases, reports):
        history = json.loads((case / "history.json").read_text())
        admitted = [row for row in history if row["max_part_k"] is not None]
        ax.plot([row["time_s"] / 3600 for row in admitted],
                [row["max_part_k"] - 273.15 for row in admitted], linewidth=.8,
                label=f"{report['pitch_mm']:g} mm, a={report['absorptivity']:g}, s={report['substeps']}")
    ax.set_xlabel("Assumed build time (h)")
    ax.set_ylabel("Maximum active bulk-part temperature (°C)")
    ax.grid(alpha=.25); ax.legend(fontsize=8)
    ax = fig.add_subplot(2, 2, 4)
    ax.axis("off")
    ax.text(0, 1, "\n".join([
        "3D finite-volume conduction + convection + radiation",
        "Partial metal cells from 1 mm geometry sampling",
        "Sequential scan/recoat phases, progressive cell activation",
        f"{reference['physical_part_layers']:,} physical 30 µm slices; {reference['cells']:,} thermal cells",
        "Hyer reference: 200 W / 1100 mm/s / 0.13 mm hatch",
        "Conventional WE43 reference: 1840 kg/m³, 966 J/kg/K, 51 W/m/K",
        f"Maximum step energy residual: {reference['maximum_step_energy_residual']:.3e}",
        f"Voxel volume error: {100*reference['voxel_relative_volume_error']:+.2f}%",
        f"Cp reference range exceeded: {reference['cp_reference_temperature_range_exceeded']}",
        f"Unvalidated numerical peak: {reference['peak_bulk_part_k'] - 273.15:.1f} °C",
        "",
        "ASSUMED absorption, supports, plate, gas and recoating time",
        "No selected machine or matched LPBF material calibration",
        "No resolved beam, phase change, powder conduction or melt flow",
        "No residual stress, release distortion or print authorization",
    ]), va="top", fontsize=10, linespacing=1.6)
    fig.text(.5, .02, "Computed macro temperatures; not laser-spot temperatures or a qualified manufacturing prediction.",
             ha="center", fontsize=10)
    fig.tight_layout(rect=(0, .04, 1, .92), h_pad=4.)
    fig.savefig(output / "thermal-study.png")
    plt.close(fig)
    manifest = {"classification": "computed_bulk_thermal_fields_uncalibrated_no_print_release",
                "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "input_summaries": [{"case": case.name,
                    "sha256": hashlib.sha256((case / "summary.json").read_bytes()).hexdigest()} for case in cases],
                "image_sha256": hashlib.sha256((output / "thermal-study.png").read_bytes()).hexdigest()}
    (output / "visuals.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.cases, args.output)
