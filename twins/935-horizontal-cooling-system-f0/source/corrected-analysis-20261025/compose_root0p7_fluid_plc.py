"""Place the corrected 0.7 rotor inside the retained exploratory fluid boundary."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from run_reconstruction import fresh, save  # noqa: E402

wall_path = SOURCE / "reference-fluid-wall-study-20261022/compose-reference-wall-001.py"
spec = importlib.util.spec_from_file_location("reference_wall", wall_path)
wall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wall)


def main(output):
    root = Path.cwd()
    rotor_path = root / "work/935-corrected-analysis-20261025/fluid-case-root-0p7-002/constant/triSurface/rotor.obj"
    parent = root / "work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz"
    assert wall.sha(rotor_path) == "ee9357d46911fc0112342626064f7e731395af9db9a8bc340793cf22effb24a6"
    assert wall.sha(parent) == "67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86"

    outer = trimesh.creation.box(extents=[2, 2, 2])
    inner = trimesh.creation.box(extents=[1, 1, 1])
    v = np.vstack([outer.vertices, inner.vertices])
    f = np.vstack([outer.faces, inner.faces[:, ::-1] + len(outer.vertices)])
    m = np.r_[np.array([1, 2] + [3] * 10), np.full(12, 4)]
    assert abs(wall.compose(v, f, m, inner.vertices, inner.faces, np.zeros(3))[3] - 7) < 1e-12

    rotor = trimesh.load_mesh(rotor_path, process=False)
    rv, rf = np.asarray(rotor.vertices), np.asarray(rotor.faces)
    assert len(rv) == 439365 and len(rf) == 878730
    with np.load(parent) as z:
        hole = z["hole"].copy()
        if abs(wall.parser.winding(rv, rf, hole) - 1) > 1e-8:
            points = rv[rf]
            normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
            areas = np.linalg.norm(normals, axis=1)
            for i in np.argsort(areas)[-20:][::-1]:
                hole = points[i].mean(axis=0) - normals[i] / areas[i] * min(.0001, np.sqrt(areas[i]) * .02)
                if abs(wall.parser.winding(rv, rf, hole) - 1) < 1e-8:
                    break
        vertices, faces, markers, volume = wall.compose(z["vertices"], z["triangles"], z["markers"], rv, rf, hole)

    out = fresh(Path(output))
    np.savez_compressed(out / "boundary.npz", vertices=vertices, triangles=faces, markers=markers, hole=hole)
    with (out / "fluid.smesh").open("x") as stream:
        stream.write(f"{len(vertices)} 3 0 0\n")
        np.savetxt(stream, np.column_stack([np.arange(len(vertices)), vertices]), fmt=["%d", "%.17g", "%.17g", "%.17g"])
        stream.write(f"{len(faces)} 1\n")
        np.savetxt(stream, np.column_stack([np.full(len(faces), 3), faces, markers]), fmt="%d")
        stream.write("1\n0 " + " ".join(f"{x:.17g}" for x in hole) + "\n0\n")
    receipt = {
        "status": "closed_exploratory_fluid_plc_pending_intersection_and_volume_quality_audits",
        "source_sha256": wall.sha(__file__),
        "reference_SI_OBJ_sha256": wall.sha(rotor_path),
        "parent_boundary_sha256": wall.sha(parent),
        "boundary_vertices": len(vertices),
        "boundary_triangles": len(faces),
        "volume_m3": volume,
        "solid_hole": hole.tolist(),
        "source_unit_m_per_uncalibrated_unit_assumed": .001,
        "physical_935_shroud_defined": False,
        "scale_verified": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
        "output_sha256": {name: wall.sha(out / name) for name in ["boundary.npz", "fluid.smesh"]},
    }
    save(out / "receipt.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: compose_root0p7_fluid_plc.py NEW_OUTPUT_DIR")
    main(sys.argv[1])
