"""Derive a lighter simulation surface from T1 (pymeshlab, recon image).

Topology-preserving quadric decimation. The output is an *input* to fTetWild,
which tolerates self-intersections inside its envelope, so defects are
reported rather than repaired. (A local delete-and-refill repair loop was
tried on 2026-11-06: it churned for 12 rounds, left open edges and changed the
genus, so it was removed rather than tuned.)

Usage: decimate.py T1.stl OUT.stl TARGET_FACES REPORT.json
"""

from __future__ import annotations

import json
import sys


def main(src, dst, target, report):
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(src)
    before = ms.current_mesh().face_number()
    ms.meshing_decimation_quadric_edge_collapse(
        targetfacenum=int(target), preserveboundary=True, preservenormal=True,
        preservetopology=True, optimalplacement=True, planarquadric=True, qualitythr=0.4,
    )
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()
    topo = ms.get_topological_measures()
    ms.compute_selection_by_self_intersections_per_face()
    self_int = ms.current_mesh().selected_face_number()
    ms.save_current_mesh(dst, binary=True)
    out = {"source_faces": before, "faces": ms.current_mesh().face_number(),
           "boundary_edges": topo["boundary_edges"],
           "non_manifold_edges": topo["non_two_manifold_edges"],
           "non_manifold_vertices": topo["non_two_manifold_vertices"],
           "genus": topo.get("genus"), "self_intersecting_faces": int(self_int),
           "use": "fTetWild input only; not an accepted surface on its own"}
    with open(report, "w") as fh:
        json.dump(out, fh, indent=2)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:5])
