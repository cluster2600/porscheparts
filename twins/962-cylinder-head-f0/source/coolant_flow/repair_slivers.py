"""Flip only deficient surface pairs, preserving their patch boundary and vertices."""
import argparse
import json
from pathlib import Path

from prepare_surface import sha

Q_MIN = 2 / 29  # Necessary surface condition for the retained SICN >= 0.1 volume target.


def triangle_q(points, faces):
    import numpy as np
    t = points[faces]
    area2 = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    lengths2 = sum(np.sum((t[:, i] - t[:, (i + 1) % 3]) ** 2, axis=1) for i in range(3))
    return np.divide(2 * np.sqrt(3) * area2, lengths2, out=np.zeros(len(t)), where=lengths2 > 0)


def repair_faces(points, faces):
    import numpy as np
    import trimesh
    faces = faces.copy(); changes = []
    def patch(face):
        x = points[face, 0]
        return "inlet" if np.all(abs(x + 76) < 1e-5) else ("outlet" if np.all(abs(x - 76) < 1e-5) else "walls")
    while True:
        q = triangle_q(points, faces)
        bad = np.flatnonzero(q < Q_MIN)
        if not len(bad): break
        model = trimesh.Trimesh(vertices=points, faces=faces, process=False)
        best = None
        for fi in bad:
            adjacent = model.face_adjacency[np.any(model.face_adjacency == fi, axis=1)]
            for pair in adjacent:
                gi = int(pair[0] if pair[1] == fi else pair[1])
                if patch(faces[fi]) != patch(faces[gi]): continue
                shared = set(faces[fi]) & set(faces[gi])
                for i in range(3):
                    u, v, a = faces[fi][[i, (i + 1) % 3, (i + 2) % 3]]
                    if {u, v} != shared: continue
                    b = next(iter(set(faces[gi]) - shared))
                    edge = sorted((a, b))
                    if np.any(np.all(model.edges_unique == edge, axis=1)): continue
                    new = np.array([[a, u, b], [a, b, v]])
                    new_q = triangle_q(points, new)
                    if min(new_q) < Q_MIN or min(new_q) <= min(q[[fi, gi]]): continue
                    old_t = points[faces[[fi, gi]]]; new_t = points[new]
                    normal = np.cross(old_t[:,1]-old_t[:,0], old_t[:,2]-old_t[:,0]).sum(axis=0)
                    if np.any(np.cross(new_t[:,1]-new_t[:,0], new_t[:,2]-new_t[:,0]) @ normal <= 0): continue
                    if any(patch(f) != patch(faces[fi]) for f in new): continue
                    if best is None or min(new_q) > best[0]: best = (float(min(new_q)), int(fi), gi, new)
        if best is None: break
        _, fi, gi, replacement = best
        changes.append(dict(faces=[fi,gi], before=faces[[fi,gi]].tolist(), after=replacement.tolist()))
        faces[[fi,gi]] = replacement
        if np.count_nonzero(triangle_q(points, faces) < Q_MIN) >= len(bad):
            raise ValueError("Repair did not strictly reduce deficient face count")
    return faces, changes


def repair(parent, output):
    import numpy as np
    import trimesh
    record = json.loads((parent / "surface-report.json").read_text())
    if not record["geometry_admitted"] or sha(parent / "coolant.stl") != record["candidate_sha256"]:
        raise ValueError("Parent surface changed or failed its screen")
    if output.exists(): raise ValueError("Output must be new")
    mesh = trimesh.load_mesh(parent / "coolant.stl", process=True)
    faces, changes = repair_faces(np.asarray(mesh.vertices), np.asarray(mesh.faces))
    proposal = trimesh.Trimesh(vertices=mesh.vertices, faces=faces, process=False)
    if not proposal.is_watertight or not proposal.is_winding_consistent or proposal.euler_number != mesh.euler_number:
        raise ValueError("Local flips changed surface topology or orientation")
    output.mkdir(parents=True)
    proposal.export(output / "coolant.stl")
    report = dict(status="local_flips_awaiting_independent_checks", source_sha256=record["source_sha256"],
                  parent_receipt_sha256=sha(parent / "surface-report.json"),
                  original_faces=record["original_faces"], faces=len(faces), flips=changes,
                  below_surface_q_gate=int(np.count_nonzero(triangle_q(mesh.vertices, faces) < Q_MIN)),
                  candidate_sha256=sha(output / "coolant.stl"), script_sha256=sha(Path(__file__)),
                  geometry_admitted=False, manufacturing_authorized=False)
    (output / "native-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(); repair(args.parent.resolve(), args.output.resolve())
