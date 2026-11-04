#!/usr/bin/env python3
"""Private orthographic source views; pixels are visualization, not inspection evidence."""
import argparse
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["selection", "frame", "boundary", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing private preview refused")
    with np.load(a.selection, allow_pickle=False) as s:
        v, f, ids = s["vertices"], s["triangles"], s["source_vertex_ids"]
    with np.load(a.boundary, allow_pickle=False) as s:
        edges, incidence = s["original_vertex_edges"], s["full_original_incidence"]
    edge_indices = np.searchsorted(ids, edges)
    if not np.array_equal(ids[edge_indices], edges):
        raise ValueError("Preview boundary is outside selected original vertices")
    abc = v @ np.load(a.frame, allow_pickle=False).T
    abc -= abc.mean(axis=0)
    normals = np.cross(abc[f[:, 1]] - abc[f[:, 0]], abc[f[:, 2]] - abc[f[:, 0]])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    text = ['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1400" viewBox="0 0 1400 1400">',
            '<rect width="1400" height="1400" fill="#101923"/>',
            '<g font-family="Helvetica,Arial,sans-serif" fill="#e8edf1">',
            '<text x="40" y="45" font-size="25">Fourth legacy search region — acquired source reference</text>',
            '<text x="40" y="78" font-size="17">2,790 original facets • open surface • anatomy unaccepted • no manufacturing release</text>']
    for panel, (axes, title) in enumerate([((0, 1, 2), "Along search C"), ((0, 2, 1), "Along search B"),
                                          ((1, 2, 0), "Along search A")]):
        x0 = 40 + (panel % 2) * 700
        y0 = 110 + (panel // 2) * 480
        xy = abc[:, axes[:2]].copy()
        scale = min(610 / np.ptp(xy[:, 0]), 390 / np.ptp(xy[:, 1]))
        xy[:, 0] = x0 + 310 + xy[:, 0] * scale
        xy[:, 1] = y0 + 240 - xy[:, 1] * scale
        text.append(f'<text x="{x0}" y="{y0 + 20}" font-size="20">{title}</text>')
        order = np.argsort(abc[f].mean(axis=1)[:, axes[2]])
        for i in order:
            shade = int(90 + 110 * abs(normals[i, axes[2]]))
            color = f"rgb({int(shade*.62)},{int(shade*.83)},{shade})"
            points = " ".join(f"{x:.2f},{y:.2f}" for x, y in xy[f[i]])
            text.append(f'<polygon points="{points}" fill="{color}" stroke="{color}" stroke-width="0.35"/>')
        for edge, uses in zip(edge_indices, incidence, strict=True):
            u, v = xy[edge]
            color = "#ff6464" if uses == 1 else "#ffc857"
            text.append(f'<line x1="{u[0]:.2f}" y1="{u[1]:.2f}" x2="{v[0]:.2f}" y2="{v[1]:.2f}" stroke="{color}" stroke-width="2"/>')
    text.extend(['<text x="750" y="690" font-size="22" fill="#ff6464">Red: original scan boundaries (140 edges)</text>',
                 '<text x="750" y="730" font-size="22" fill="#ffc857">Gold: selection cuts (144 edges)</text>',
                 '<text x="750" y="790" font-size="18">Original positions and triangles retained.</text>',
                 '<text x="750" y="825" font-size="18">No cylinder, gap fill or hidden gallery inferred.</text>',
                 '<text x="750" y="860" font-size="18">Search axes are not accepted physical datums.</text>',
                 '<text x="40" y="1090" font-size="16">Private acquired geometry • source and native geometry are checked separately; this image is illustrative.</text>',
                 '</g></svg>'])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as stream:
        stream.write("\n".join(text) + "\n")
    print("Private source-reference SVG written.")


if __name__ == "__main__":
    main()
