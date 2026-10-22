"""Use every analysis-reference triangle as the solid hole of the fluid PLC."""
import hashlib
import json
import signal
from pathlib import Path

import numpy as np
import trimesh
from run_reconstruction import fresh, save
from agglomerate_fluid_pairs import ascii as parser

signal.alarm(300)
sha = lambda p: hashlib.file_digest(Path(p).open('rb'), 'sha256').hexdigest()


def compose(vertices, faces, markers, rotor_vertices, rotor_faces, hole):
    if set(np.unique(markers)) != {1, 2, 3, 4}:
        raise ValueError('Four original physical patch markers required')
    rotor = trimesh.Trimesh(vertices=rotor_vertices, faces=rotor_faces, process=False)
    if not rotor.is_watertight or not rotor.is_winding_consistent or rotor.volume <= 0:
        raise ValueError('Closed consistently outward-oriented rotor required')
    outer = faces[markers != 4]
    used = np.unique(outer)
    mapping = np.full(len(vertices), -1, dtype=np.int64)
    mapping[used] = np.arange(len(used))
    points = np.vstack([vertices[used], rotor_vertices])
    triangles = np.vstack([mapping[outer], rotor_faces[:, ::-1] + len(used)])
    tags = np.r_[markers[markers != 4], np.full(len(rotor_faces), 4, dtype=np.int32)]
    fluid = trimesh.Trimesh(vertices=points, faces=triangles, process=False)
    if not fluid.is_watertight or not fluid.is_winding_consistent or fluid.volume <= 0:
        raise ValueError('Closed consistently oriented positive fluid PLC required')
    if abs(parser.winding(rotor_vertices, rotor_faces, hole) - 1) > 1e-8 or abs(parser.winding(points, triangles, hole)) > 1e-8:
        raise ValueError('Independent solid-hole and fluid winding tests required')
    assert np.array_equal(points[len(used):], rotor_vertices)
    assert np.array_equal(triangles[tags == 4][:, ::-1] - len(used), rotor_faces)
    assert np.array_equal(points[triangles[tags != 4]], vertices[faces[markers != 4]])
    return points, triangles, tags, float(fluid.volume)


if __name__ == '__main__':
    # Analytic nested boxes independently check orientation, subtraction and the solid hole.
    outer = trimesh.creation.box(extents=[2, 2, 2])
    inner = trimesh.creation.box(extents=[1, 1, 1])
    v = np.vstack([outer.vertices, inner.vertices])
    f = np.vstack([outer.faces, inner.faces[:, ::-1] + len(outer.vertices)])
    m = np.r_[np.array([1, 2] + [3] * 10), np.full(12, 4)]
    assert abs(compose(v, f, m, inner.vertices, inner.faces, np.zeros(3))[3] - 7) < 1e-12
    try:
        compose(v, f, m, inner.vertices, inner.faces[:-1], np.zeros(3))
    except ValueError:
        pass
    else:
        raise AssertionError('Open rotor must be refused')
    root = Path.cwd()
    source = root / 'work/935-cfd-pilot-20261022/rotor-001/coarse/constant/triSurface/rotor.obj'
    parent = root / 'work/935-cfd-mesh-correction-20261022/prepared-concavity20-001'
    assert sha(source) == '5eb9ee8a73b140198013fe511916c150316acc8e31174a2ca1fea4bac4db3e44'
    assert sha(parent / 'boundary.npz') == '67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86'
    proof = json.loads((parent / 'receipt.json').read_text())
    assert sha(parent / 'boundary.npz') == proof['output_sha256']['boundary.npz']
    reference = trimesh.load_mesh(source, process=False)
    rv, rf = np.asarray(reference.vertices), np.asarray(reference.faces)
    assert len(rv) == 436712 and len(rf) == 873444 and np.isfinite(rv).all()
    with np.load(parent / 'boundary.npz') as z:
        hole = z['hole'].copy()
        if abs(parser.winding(rv, rf, hole) - 1) > 1e-8:
            points = rv[rf]
            normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
            areas = np.linalg.norm(normals, axis=1)
            for i in np.argsort(areas)[-20:][::-1]:
                hole = points[i].mean(axis=0) - normals[i] / areas[i] * min(.0001, np.sqrt(areas[i]) * .02)
                if abs(parser.winding(rv, rf, hole) - 1) < 1e-8:
                    break
        vertices, faces, markers, volume = compose(z['vertices'], z['triangles'], z['markers'], rv, rf, hole)
    assert abs(parser.winding(vertices, faces, np.array([-.17, .17, .18])) - 1) < 1e-8
    out = fresh(root / 'work/935-reference-fluid-wall-20261022/prepared-001')
    np.savez_compressed(out / 'boundary.npz', vertices=vertices, triangles=faces, markers=markers, hole=hole)
    with (out / 'boundary.obj').open('x') as stream:
        np.savetxt(stream, vertices, fmt='v %.17g %.17g %.17g')
        np.savetxt(stream, faces + 1, fmt='f %d %d %d')
    with (out / 'fluid.smesh').open('x') as stream:
        stream.write(f'{len(vertices)} 3 0 0\n')
        np.savetxt(stream, np.column_stack([np.arange(len(vertices)), vertices]), fmt=['%d', '%.17g', '%.17g', '%.17g'])
        stream.write(f'{len(faces)} 1\n')
        np.savetxt(stream, np.column_stack([np.full(len(faces), 3), faces, markers]), fmt='%d')
        stream.write('1\n0 ' + ' '.join(f'{x:.17g}' for x in hole) + '\n0\n')
    record = {'status': 'exact_reference_rotor_with_retained_outer_duct_pending_intersection_and_volume_audits', 'source_sha256': sha(__file__), 'reference_SI_OBJ_sha256': sha(source), 'parent_receipt_sha256': sha(parent / 'receipt.json'), 'boundary_vertices': len(vertices), 'triangles': len(faces), 'rotor_vertices': len(rv), 'rotor_triangles': len(rf), 'reference_rotor_coordinates_and_reversed_triangles_exact': True, 'outer_boundary_coordinates_triangles_markers_unchanged': True, 'analytic_nested_box_control_volume_m3': 7., 'open_rotor_refusal_control_passed': True, 'volume_m3': volume, 'previous_snapped_volume_m3': proof['volume_m3'], 'solid_hole': hole.tolist(), 'source_unit_m_per_uncalibrated_unit_assumed': .001, 'actual_935_housing_defined': False, 'scale_verified': False, 'CFD_accepted': False, 'manufacturing_authorized': False, 'output_sha256': {n: sha(out / n) for n in ['boundary.npz', 'boundary.obj', 'fluid.smesh']}}
    save(out / 'receipt.json', record)
    print(json.dumps(record), flush=True)
