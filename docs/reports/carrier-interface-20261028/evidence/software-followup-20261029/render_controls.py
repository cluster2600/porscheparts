"""Render recorded controls; requires matplotlib and no private geometry."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    root = Path(__file__).resolve().parent
    controls = json.loads((root / "analytical-controls.json").read_text())
    precision = json.loads((root / "precision-summary.json").read_text())
    with plt.style.context("seaborn-v0_8-whitegrid"):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
        for name in ("cube", "thin-notch", "thin-air-fin"):
            rows = [r for r in controls["cases"] if r["case"] == name]
            axes[0].plot(
                [r["h_mm"] for r in rows],
                [r["complete_implicit_residual_bound_mm"] for r in rows],
                marker="o", label=name,
            )
        axes[0].set(xlabel="Grid size (mm)", ylabel="Complete residual bound (mm)",
                    title="Nine analytical controls passed")
        axes[0].legend()
        frames = precision["frames"]
        bars = axes[1].bar([r["frame"] for r in frames],
                           [r["collapsed_faces"] for r in frames], color="#b5473e")
        axes[1].bar_label(bars, padding=4)
        axes[1].set(ylabel="Collapsed triangles after float32 conversion",
                    ylim=(0, 1100), title="Both STL handoffs refused")
        fig.suptitle("993 carrier — software checks, unchanged 1.2933916 kg reference")
        output = root.parents[3] / "media/carrier-interface-20261028/software-followup-controls.png"
        fig.savefig(output, dpi=150)
        plt.close(fig)
        print(output)


if __name__ == "__main__":
    main()
