"""One complete clipped-array/provenance census; no repair or geometry output."""
import ast
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
HELPER = 'twins/962-cylinder-head-f0/source/audit_quality_head.py'
HELPER_SHA = 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991'
CHUNK = 65536


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def plane_classes(points, faces):
    count = np.count_nonzero(points[faces, 2] == 0, axis=1)
    return {'cap_all_z0': count == 3,
            'noncap_mixed_plane_vertices': (count > 0) & (count < 3),
            'noncap_no_plane_vertices': count == 0}


def verify(contract):
    for name, digest in contract['input_hashes'].items():
        relative = Path(name)
        path = ROOT / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.is_file() or sha(path) != digest):
            raise ValueError('Bound clipped-readback input drift: ' + name)
    if sha(Path(sys.executable).resolve()) != contract['runtime']['python_executable_sha256']:
        raise ValueError('Selected reader interpreter changed')


def load_helpers():
    path = ROOT / HELPER
    if sha(path) != HELPER_SHA:
        raise ValueError('Whole retained read/qualities helper changed')
    tree = ast.parse(path.read_text())
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in ('read', 'qualities')]
    if len(functions) != 2 or {node.name for node in functions} != {'read', 'qualities'}:
        raise ValueError('Exact retained helper definitions required')
    namespace = {'np': np, 'struct': struct}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['read'], namespace['qualities']


def surface_stats(points, faces, quality):
    referenced = np.zeros(len(points), dtype=bool)
    volume_terms = []
    cap_areas = []
    cap_nonnegative_normal = 0
    rows = {name: {'faces': 0, 'poor_faces': 0, 'minimum_quality': None,
                   'poor_face_ids': [], 'poor_vertex_ids_sha256': None,
                   'poor_vertices': 0}
            for name in ('cap_all_z0', 'noncap_mixed_plane_vertices', 'noncap_no_plane_vertices')}
    all_classes = {name: np.zeros(len(faces), dtype=bool) for name in rows}
    for start in range(0, len(faces), CHUNK):
        triangles = faces[start:start + CHUNK]
        if np.any(triangles[:, 0] == triangles[:, 1]) or np.any(triangles[:, 1] == triangles[:, 2]) or np.any(triangles[:, 2] == triangles[:, 0]):
            raise ValueError('Repeated vertex in triangle')
        referenced[triangles.ravel()] = True
        xyz = points[triangles]
        cross = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
        terms = np.einsum('ij,ij->i', xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2])) / 6
        if not np.isfinite(cross).all() or not np.isfinite(terms).all():
            raise ValueError('Nonfinite independent area or volume arithmetic')
        volume_terms.append(math.fsum(terms))
        classes = plane_classes(points, triangles)
        for name, mask in classes.items():
            all_classes[name][start:start + len(triangles)] = mask
        cap = classes['cap_all_z0']
        cap_areas.append(math.fsum(np.linalg.norm(cross[cap], axis=1) / 2))
        cap_nonnegative_normal += int(np.count_nonzero(cross[cap, 2] >= 0))
    if not referenced.all():
        raise ValueError('Unreferenced source or clipped vertex')
    # Undirected equality also detects reversed duplicate faces; cyclic starts do not matter.
    keys = np.ascontiguousarray(np.sort(faces, axis=1), dtype='<u8').view('V24').ravel()
    if len(np.unique(keys)) != len(faces):
        raise ValueError('Duplicate triangle coordinates/indices')
    if len(np.unique(points, axis=0)) != len(points):
        raise ValueError('Duplicate numeric coordinates')
    poor = quality < 2 / 29
    seeds = np.unique(faces[poor])
    seed_mask = np.zeros(len(points), dtype=bool)
    seed_mask[seeds] = True
    patch = np.zeros(len(faces), dtype=bool)
    for start in range(0, len(faces), CHUNK):
        patch[start:start + CHUNK] = np.any(seed_mask[faces[start:start + CHUNK]], axis=1)
    fixed = np.zeros(len(points), dtype=bool)
    fixed[faces[~patch].ravel()] = True
    fixed |= (points[:, 0] == -76) | (points[:, 0] == 76)
    for name, mask in all_classes.items():
        selected = mask & poor
        ids = np.flatnonzero(selected)
        vertices = np.unique(faces[selected])
        rows[name].update(faces=int(np.count_nonzero(mask)), poor_faces=len(ids),
                          minimum_quality=float(quality[mask].min()) if np.any(mask) else None,
                          poor_face_ids=ids.tolist(), poor_vertices=len(vertices),
                          poor_vertex_ids_sha256=array_sha(vertices))
    if sum(row['faces'] for row in rows.values()) != len(faces) or sum(row['poor_faces'] for row in rows.values()) != int(np.count_nonzero(poor)):
        raise ValueError('Incomplete plane/poor partition')
    total = math.fsum(volume_terms)
    if not math.isfinite(total) or total <= 0:
        raise ValueError('Finite positive global signed volume required')
    return dict(vertices=len(points), faces=len(faces), bounds_mm=[points.min(axis=0).tolist(), points.max(axis=0).tolist()],
                minimum_quality=float(quality.min()), faces_below_2_over_29=int(np.count_nonzero(poor)),
                quality_formula='unchanged retained audit_quality_head.qualities; NumPy arithmetic distinct from native CGAL',
                signed_volume_mm3=total, signed_volume_sum_method='math.fsum per 65536-face chunk, then math.fsum of chunk totals',
                cap_area_mm2=math.fsum(cap_areas), cap_nonnegative_Z_normals=cap_nonnegative_normal,
                plane_classes=rows, zero_orphan_vertices=True, zero_duplicate_numeric_coordinates=True,
                zero_duplicate_unoriented_faces=True, all_triangles_finite_nondegenerate=True,
                poor_seed_vertices=len(seeds), poor_seed_vertex_ids_sha256=array_sha(seeds),
                exact_incident_patch_faces=int(np.count_nonzero(patch)), exact_incident_patch_mask_sha256=array_sha(patch),
                exterior_fixed_plus_original_x_clip_vertices=int(np.count_nonzero(fixed)), fixed_mask_sha256=array_sha(fixed),
                patch_component_or_disk_census_computed=False)


def main():
    path = OUT / 'frozen-contract.json'
    contract = json.loads(path.read_text())
    contract_sha = sha(path)
    if contract.get('readback_launch_authorized') is not True or OUT != (ROOT / contract['expected_fresh_output']).resolve():
        raise ValueError('Separate reviewed exact reader launch and fresh fixed output required')
    if (OUT / 'readback-report.json').exists() or (OUT / 'readback-report.json').is_symlink():
        raise ValueError('Existing readback preserved')
    verify(contract)
    if sha(Path(__file__)) != contract['reader_sha256'] or sha(OUT / 'run_readback.py') != contract['runner_sha256']:
        raise ValueError('Executed reader/runner changed')
    if platform.machine() != 'arm64' or np.__version__ != contract['runtime']['numpy_version']:
        raise ValueError('Retained ARM/NumPy runtime version required')
    read, qualities = load_helpers()
    started = time.monotonic()
    p, f = read(ROOT / contract['original'])
    q, g = read(ROOT / contract['candidate'])
    if (len(p), len(f), len(q), len(g)) != (901727, 1803870, 869355, 1739126):
        raise ValueError('Bound complete input/output counts differ')
    map_path = ROOT / contract['clip_coordinate_ids']
    if map_path.stat().st_size != 8 * len(q):
        raise ValueError('Complete clip-coordinate map required')
    ids = np.memmap(map_path, mode='r', dtype='<u8', shape=(len(q),))
    retained = ids != np.iinfo(np.uint64).max
    known = ids[retained]
    if len(known) != 865847 or len(np.unique(known)) != len(known) or np.any(known >= len(p)):
        raise ValueError('Unique valid retained clip-input IDs required')
    if q[retained].tobytes() != p[known].tobytes():
        raise ValueError('Every retained coordinate must match all original bytes')
    if int(np.count_nonzero(~retained)) != 3508 or np.any(q[~retained, 2] != 0) or np.any(q[:, 2] < 0):
        raise ValueError('Constructed points must be exactly on z0; output must be above plane')
    point_keys = np.ascontiguousarray(p).view('V24').ravel()
    new_keys = np.ascontiguousarray(q[~retained]).view('V24').ravel()
    if np.any(np.isin(new_keys, point_keys)):
        raise ValueError('Sentinel point has an exact existing input-coordinate identity')
    original_stats = surface_stats(p, f, qualities(p, f))
    candidate_stats = surface_stats(q, g, qualities(q, g))
    if candidate_stats['cap_nonnegative_Z_normals']:
        raise ValueError('Strictly outward negative-Z cap required')
    native = json.loads((ROOT / contract['native_report']).read_text())
    report = dict(status='complete_clipped_array_census_only', scope='No repair or independent global admission',
                  original=original_stats, candidate=candidate_stats,
                  full_array_sha256={name: array_sha(a) for name, a in zip(('original_points', 'original_faces', 'candidate_points', 'candidate_faces', 'clip_coordinate_ids'), (p, f, q, g, ids))},
                  exact_retained_coordinate_matches=len(known), constructed_z0_coordinate_count=int(np.count_nonzero(~retained)),
                  clip_ids_are_coordinate_matches_not_construction_history=True, sentinel_not_used_as_input_index=True,
                  native_report_sha256=contract['input_hashes'][contract['native_report']],
                  retained_native_minimum_quality=native['minimum_surface_quality'],
                  retained_native_faces_below_2_over_29=native['surface_faces_below_2_over_29'],
                  NumPy_and_native_poor_counts_equal=candidate_stats['faces_below_2_over_29'] == native['surface_faces_below_2_over_29'],
                  independent_minus_native_volume_mm3=candidate_stats['signed_volume_mm3'] - native['output_signed_volume_mm3'],
                  independent_minus_native_cap_area_mm2=candidate_stats['cap_area_mm2'] - native['plane_cap_area_mm2'],
                  cap_face_count_matches_native=candidate_stats['plane_classes']['cap_all_z0']['faces'] == native['plane_cap_faces'],
                  runtime=dict(python_executable_sha256=sha(Path(sys.executable).resolve()), numpy=np.__version__, machine=platform.machine()),
                  helper_whole_source_sha256=HELPER_SHA, helper_definitions_extracted=['read', 'qualities'],
                  global_topology_intersection_CUB_or_feature_admission=False, surface_or_volume_mesh_admitted=False,
                  thermal_strength_process_or_manufacturing_qualified=False, mesh_or_geometry_files_written=0,
                  scientific_geometry_or_PDE_calls=0)
    verify(contract)
    if sha(path) != contract_sha or sha(Path(__file__)) != contract['reader_sha256']:
        raise ValueError('Contract/reader changed during census')
    report.update(all_bound_inputs_unchanged=True, readback_wall_seconds=time.monotonic() - started)
    with (OUT / 'readback-report.json').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'clipped_poor_faces': candidate_stats['faces_below_2_over_29']}))


if __name__ == '__main__':
    main()
