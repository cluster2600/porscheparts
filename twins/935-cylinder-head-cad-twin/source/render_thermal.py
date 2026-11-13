"""Private screenshot of a thermal screen: boundary temperatures, four views.

Usage: render_thermal.py WORKDIR OUT.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_thermal_balance import parse_deck, read_temps  # noqa: E402
from render_views import grid_shots  # noqa: E402
from sim_thermal import boundary_faces  # noqa: E402


def main(work, out):
    import pyvista as pv

    work = Path(work)
    nodes, elems, _ = parse_deck(work / "head.inp")
    temps = read_temps(work / "head.frd")
    tag = nodes[:, 0].astype(np.int64)
    order = np.argsort(tag)
    tag, xyz = tag[order], nodes[order, 1:]
    _, _, tri = boundary_faces(elems)
    idx = np.searchsorted(tag, tri)
    used, inv = np.unique(idx, return_inverse=True)
    surf = pv.PolyData(xyz[used], np.column_stack((np.full(len(tri), 3), inv.reshape(-1, 3))).ravel())
    surf.point_data["T_C"] = np.array([temps[int(t)] for t in tag[used]])
    grid_shots([(surf, {"scalars": "T_C", "cmap": "inferno", "scalar_bar_args": {"title": "T (degC)"}})],
               out, "Steady thermal screen, 1.0 mm level, declared hypotheses (uncorrelated)")
    print("written", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
