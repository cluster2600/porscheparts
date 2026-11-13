"""Make T1s intersection-free by reverting snapped vertices locally to T1.

T1 (marching cubes) has no self-intersection; T1s shares its connectivity.
Each round finds the self-intersecting faces of the current surface, grows the
selection by one ring, and puts those vertices back at their T1 positions.
Because T1 is intersection-free, the loop terminates. Runs in the recon image
(pymeshlab).

Usage: unsnap_intersections.py T1.ply T1S.ply OUT.ply REPORT.json
"""

from __future__ import annotations

import json
import sys

import numpy as np

MAX_ROUNDS = 50


def main(t1, t1s, out, report):
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(t1)
    v_ref = ms.current_mesh().vertex_matrix().copy()
    f = ms.current_mesh().face_matrix().copy()
    ms.load_new_mesh(t1s)
    v = ms.current_mesh().vertex_matrix().copy()
    if not np.array_equal(f, ms.current_mesh().face_matrix()):
        raise SystemExit("T1 and T1s connectivity differ")
    v_snapped = v.copy()
    ms.clear()
    rounds = []
    for _ in range(MAX_ROUNDS):
        ms.add_mesh(pymeshlab.Mesh(vertex_matrix=v, face_matrix=f))
        ms.compute_selection_by_self_intersections_per_face()
        n_bad = ms.current_mesh().selected_face_number()
        rounds.append(int(n_bad))
        if n_bad == 0:
            break
        ms.apply_selection_dilatation()
        sel = ms.current_mesh().face_selection_array()
        idx = np.unique(f[sel])
        v[idx] = v_ref[idx]
        ms.clear()
    else:
        raise SystemExit("did not converge")
    ms.save_current_mesh(out, binary=True)
    reverted = int((v != v_snapped).any(axis=1).sum())
    rep = {"rounds": rounds, "vertices_reverted_to_t1": reverted, "final_self_intersecting_faces": rounds[-1]}
    with open(report, "w") as fh:
        json.dump(rep, fh, indent=2)
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:5])
