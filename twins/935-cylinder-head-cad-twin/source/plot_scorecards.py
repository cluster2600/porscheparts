"""Public chart: share of the acquired scan within 0.2 mm of each twin body.

Reads committed scorecards only (scalars), so the chart rebuilds anywhere. One
measure, one series: a horizontal bar per body, value at the bar tip.

Usage: plot_scorecards.py PARAMS_DIR OUT.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BODIES = (
    ("T1s reference surface (snapped)", "scorecard-t1s.json"),
    ("T1 reference surface", "scorecard-t1.json"),
    ("v2 CAD body, sections 0.25 mm apart", "scorecard-v2-loft-s025.json"),
    ("v2 CAD body, sections 0.5 mm apart", "scorecard-v2-loft-s050.json"),
    ("v2 CAD body, sections 1.0 mm apart", "scorecard-v2-loft-s100.json"),
    ("v1 prism stack, run f", "scorecard-v1-stack-f-shell.json"),
)
SURFACE, INK, MUTED, BAR = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6"


def shares(params):
    return [(name, json.loads((Path(params) / file).read_text())["scan_to_twin"]["area_share_within_mm"]["0.2"],
             json.loads((Path(params) / file).read_text())["scan_to_twin"]["p95"]) for name, file in BODIES]


def main(params, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    rows = shares(params)[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 3.6), dpi=160, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    thick = 0.42
    for y, (name, share, p95) in enumerate(rows):
        pct = 100.0 * share
        bar = FancyBboxPatch((-3.0, y - thick / 2), pct + 3.0, thick, boxstyle="round,pad=0,rounding_size=0.9",
                             mutation_aspect=thick / 6.0, linewidth=0, facecolor=BAR, clip_on=True)
        ax.add_patch(bar)
        ax.text(pct + 1.2, y, f"{pct:.1f}%", va="center", ha="left", fontsize=9.5, color=INK)
        ax.text(113.0, y, f"p95 {p95:.3f} mm", va="center", ha="left", fontsize=8.5, color=MUTED)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9.5, color=INK)
    ax.set_xlim(0, 132)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"], fontsize=8.5, color=MUTED)
    ax.xaxis.grid(True, color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Acquired scan area within 0.2 mm of each twin body", loc="left", fontsize=11, color=INK, pad=10)
    fig.text(0.012, 0.015, "146,967 mm² of acquired surface, studs excluded; distances to the scan only.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, facecolor=SURFACE)


if __name__ == "__main__":
    main(*sys.argv[1:3])
