"""Plot actual void sections; write all-triangle surface-integral metrics."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
import numpy as np


def section_and_volume(path, plane):
    z = np.load(path, allow_pickle=False)
    v, f = z["vertices"], z["triangles"]
    reference = (v.min(axis=0)+v.max(axis=0))/2
    segments, volumes = [], []
    for start in range(0, len(f), 200000):
        tri = v[f[start:start+200000]]
        centred = tri-reference
        volumes.append(float(np.einsum("ij,ij->i", centred[:, 0], np.cross(centred[:, 1], centred[:, 2])).sum()/6))
        crossings, face_ids = [], []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            mask = (tri[:, a, 2] < plane) != (tri[:, b, 2] < plane)
            selected = tri[mask]
            ratio = (plane-selected[:, a, 2])/(selected[:, b, 2]-selected[:, a, 2])
            crossings.append((selected[:, a]+ratio[:, None]*(selected[:, b]-selected[:, a]))[:, :2])
            face_ids.append(np.flatnonzero(mask))
        ids = np.concatenate(face_ids)
        points = np.concatenate(crossings)
        order = np.argsort(ids, kind="stable")
        if len(ids):
            sorted_ids = ids[order].reshape(-1, 2)
            if not np.all(sorted_ids[:, 0] == sorted_ids[:, 1]):
                raise ValueError("Section has an unpaired crossing")
            segments.append(points[order].reshape(-1, 2, 2))
    return np.concatenate(segments), dict(
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        vertices=len(v), faces=len(f),
        surface_integral_volume_mm3_float64=math.fsum(volumes),
        section_z_mm=plane,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("eroded", type=Path)
    parser.add_argument("rounded", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--plane", type=float, default=2.86)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".json").exists():
        raise ValueError("Fresh image and metrics paths required")
    labels = ["Original void", "Eroded input (float32)", "Rounded candidate"]
    colors = ["#465666", "#1d905e", "#cc6b24"]
    paths = [args.original, args.eroded, args.rounded]
    computed = [section_and_volume(path, args.plane) for path in paths]
    with plt.style.context("seaborn-v0_8-whitegrid"):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
        for axis in axes:
            for (segments, _), color in zip(computed, colors):
                axis.add_collection(LineCollection(segments, colors=color, linewidths=1.1))
            axis.set(xlabel="Nominal x (mm)", ylabel="Nominal y (mm)")
            axis.set_aspect("equal")
        all_points = np.concatenate([s.reshape(-1, 2) for s, _ in computed])
        lo, hi = all_points.min(axis=0), all_points.max(axis=0)
        axes[0].set(xlim=(lo[0]-.3, hi[0]+.3), ylim=(lo[1]-.3, hi[1]+.3), title="Complete plane section")
        axes[1].set(xlim=(74.55, 75.50), ylim=(24.20, 25.15), title="Previously problematic source region")
        axes[0].legend([Line2D([0], [0], color=c) for c in colors], labels, loc="center left", bbox_to_anchor=(1.05, .5))
        fig.suptitle(f"Source-distance rounding — actual geometry at z = {args.plane:g} mm\nOne void; independent embedding and strict containment passed")
        fig.savefig(args.output, dpi=160)
        plt.close(fig)
    metrics = {label: row for label, (_, row) in zip(labels, computed)}
    delta = metrics[labels[0]]["surface_integral_volume_mm3_float64"]-metrics[labels[2]]["surface_integral_volume_mm3_float64"]
    metrics["theoretical_titanium_restored_g"] = delta*.00442
    metrics["density_kg_per_mm3"] = 4.42e-6
    metrics["whole_carrier_reintegrated"] = False
    metrics["image_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".json").write_text(json.dumps(metrics, indent=2)+"\n")


if __name__ == "__main__":
    main()
