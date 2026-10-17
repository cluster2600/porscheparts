"""Held d2af-to-9d62 region continuity; exact exterior and boundary, no semantic map."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve(); PREP = HERE.parent
OUTPUT = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-001'
MAX = (1 << 64)-1
CHUNK = 65536
np = None
patch_topology = None
FILES = {
    'before': 'work/962-engineering/atomic-cavity-plane-clip-exact-head-001/head-plane0/candidate.bin',
    'after': 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin',
    'region_authority': 'work/962-engineering/atomic-cavity-plane-clip-patch-census-001/readback-report.json',
    'cap_authority': 'work/962-engineering/atomic-cavity-plane-clip-repair-reference-001/readback-report.json',
    'assembly': 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/manifest.json',
    'coordinate_origins': 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/vertex-coordinate-origins.u64',
    'face_sources': 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/face-source-ids.u64',
    'candidate_cap_faces': 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/cap-to-head-faces.u64',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"962SURF1":
        raise ValueError("Complete binary indexed surface required")
    nv, nf = struct.unpack_from("<QQ", header, 8)
    if not nv or not nf or path.stat().st_size != 24+24*(nv+nf):
        raise ValueError("Complete surface payload and counts required")
    p = np.memmap(path, mode="r", dtype="<f8", offset=24, shape=(nv, 3))
    f = np.memmap(path, mode="r", dtype="<u8", offset=24+24*nv, shape=(nf, 3))
    if not np.isfinite(p).all() or f.max() >= nv:
        raise ValueError("Finite valid coordinate/index arrays required")
    return p, f


def canonical_faces(f):
    rows = np.asarray(f).copy()
    shifts = np.argmin(rows, axis=1)
    return np.take_along_axis(rows, (np.arange(3)[None, :]+shifts[:, None]) % 3, axis=1)


def array_sha(rows):
    return hashlib.sha256(np.ascontiguousarray(rows).tobytes()).hexdigest()


def sorted_directed_edges(edges):
    rows = np.asarray(edges, dtype='<u8').reshape(-1, 2)
    return rows[np.lexsort((rows[:, 1], rows[:, 0]))]


def coordinate_boundary_sha(points, boundary):
    rows = np.ascontiguousarray(points[boundary], dtype='<f8').reshape(-1, 6)
    keys = rows.view('V48').ravel()
    return hashlib.sha256(np.sort(keys).tobytes()).hexdigest()


def compare_region(p, f, q, g, region_ids, origins, face_sources, fixed_faces):
    """One declared connected region; new interior IDs never enter original indexing."""
    region_ids = np.asarray(region_ids, dtype='<u8')
    fixed_faces = np.asarray(fixed_faces, dtype='<u8')
    if (not len(region_ids) or region_ids.ndim != 1 or
            not np.array_equal(region_ids, np.unique(region_ids)) or region_ids[-1] >= len(f) or
            fixed_faces.ndim != 1 or not np.array_equal(fixed_faces, np.unique(fixed_faces)) or
            (len(fixed_faces) and fixed_faces[-1] >= len(f)) or
            origins.dtype != np.dtype('<u8') or origins.shape != (len(q),) or
            face_sources.dtype != np.dtype('<u8') or face_sources.shape != (len(g),)):
        raise ValueError('Complete sorted region/fixed IDs and full provenance arrays required')
    known_vertices = origins != MAX
    if (np.any(origins[known_vertices] >= len(p)) or
            len(np.unique(origins[known_vertices])) != int(known_vertices.sum())):
        raise ValueError('Known coordinate origins must be unique and in range')
    known_ids = np.flatnonzero(known_vertices)
    for start in range(0, len(known_ids), CHUNK):
        ids = known_ids[start:start+CHUNK]
        if q[ids].tobytes() != p[origins[ids]].tobytes():
            raise ValueError('Retained coordinate bytes changed')
    old_mask = np.zeros(len(f), dtype=np.bool_); old_mask[region_ids] = True
    if np.any(old_mask[fixed_faces]):
        raise ValueError('Declared fixed exterior cells overlap the old region')
    known_faces = face_sources != MAX
    if (np.any(face_sources[known_faces] >= len(f)) or
            len(np.unique(face_sources[known_faces])) != int(known_faces.sum())):
        raise ValueError('Known face source IDs must be unique and in range')
    new_mask = ~known_faces
    # MAX is never used as a boolean-mask or original-surface index.
    new_mask[known_faces] = old_mask[face_sources[known_faces]]
    selected = np.flatnonzero(new_mask)
    exterior_ids = np.flatnonzero(~old_mask).astype('<u8')
    candidate_exterior = np.flatnonzero(~new_mask)
    order = np.argsort(face_sources[candidate_exterior])
    candidate_exterior = candidate_exterior[order]
    if not np.array_equal(face_sources[candidate_exterior], exterior_ids):
        raise ValueError('Complete exterior face-source bijection failed')
    exterior_hash = hashlib.sha256()
    for start in range(0, len(exterior_ids), CHUNK):
        old_ids = exterior_ids[start:start+CHUNK]; new_ids = candidate_exterior[start:start+CHUNK]
        mapped = origins[g[new_ids]]
        if (np.any(mapped == MAX) or
                not np.array_equal(canonical_faces(mapped), canonical_faces(f[old_ids]))):
            raise ValueError('Exact oriented exterior triangles changed')
        exterior_hash.update(np.ascontiguousarray(f[old_ids], dtype='<u8').tobytes())
    before, boundary = patch_topology(f[region_ids])
    after, other = patch_topology(g[selected])
    invariants = ['components', 'euler_characteristic', 'boundary_loops',
                  'boundary_vertices', 'boundary_edges', 'vertex_link_manifold']
    if any(before[key] != after[key] for key in invariants):
        raise ValueError('Measured region topology or boundary signature changed')
    mapped_boundary = origins[other]
    if np.any(mapped_boundary == MAX):
        raise ValueError('New/MAX point on the frozen region boundary')
    if not np.array_equal(sorted_directed_edges(mapped_boundary), sorted_directed_edges(boundary)):
        raise ValueError('Exact oriented region boundary identity changed')
    boundary_before_sha = coordinate_boundary_sha(p, boundary)
    boundary_after_sha = coordinate_boundary_sha(q, other)
    if boundary_before_sha != boundary_after_sha:
        raise ValueError('Complete oriented boundary coordinate bytes changed')
    fixed_new = np.flatnonzero(np.isin(face_sources, fixed_faces)).astype('<u8')
    if len(fixed_new) != len(fixed_faces) or np.any(new_mask[fixed_new]):
        raise ValueError('Every frozen cap cell must remain once in the exterior')
    return dict(before=before, after=after,
        delta_VEF={key: after[key]-before[key] for key in ['vertices', 'edges', 'faces']},
        original_region_face_ids=region_ids.tolist(), candidate_region_face_ids=selected.tolist(),
        original_region_mask_sha256=array_sha(old_mask), candidate_region_mask_sha256=array_sha(new_mask),
        exterior_faces=len(exterior_ids), exact_original_exterior_rows_sha256=exterior_hash.hexdigest(),
        exterior_candidate_IDs_in_original_source_order_sha256=array_sha(candidate_exterior.astype('<u8')),
        complete_exterior_oriented_triangles_and_coordinate_bytes_unchanged=True,
        known_original_coordinate_points=int(known_vertices.sum()), new_local_coordinate_points=int((~known_vertices).sum()),
        original_oriented_boundary_ID_sha256=array_sha(sorted_directed_edges(boundary)),
        mapped_candidate_oriented_boundary_ID_sha256=array_sha(sorted_directed_edges(mapped_boundary)),
        original_boundary_coordinate_rows_sha256=array_sha(p[np.unique(boundary)]),
        oriented_boundary_coordinate_multiset_sha256=boundary_before_sha,
        complete_boundary_coordinate_signatures_equal=True,
        fixed_original_cap_face_ids=fixed_faces.tolist(), fixed_candidate_cap_face_ids=fixed_new.tolist(),
        fixed_cap_cells_exactly_preserved=True, new_MAX_points_used_as_original_indices=False)


def validate(path, expected):
    if digest(path) != expected:
        raise ValueError('Exact frozen child required')
    c = json.loads(path.read_text())
    if (c.get('schema') != '962-stage-local-feature-continuity-child/v1' or
            c.get('root_authorized') is not True or c.get('root_and_peer_review_complete') is not True):
        raise ValueError('HELD: reviewed root authorization required before inputs or NumPy')
    held_path = PREP/'held-contract.json'; held = json.loads(held_path.read_text())
    if c.get('preparation') != dict(path=str(held_path.relative_to(ROOT)), sha256=digest(held_path)):
        raise ValueError('Exact held preparation required')
    pins = dict(held['input_sha256']); pins[str(held_path.relative_to(ROOT))] = digest(held_path)
    for name, value in c.get('execution_reviews', {}).items():
        if name in pins:
            raise ValueError('Review must not replace a prepared input')
        pins[name] = value
    if (c.get('input_sha256') != pins or c.get('paths') != FILES or
            c.get('output') != str(OUTPUT.relative_to(ROOT)) or c.get('automatic_retry') is not False or
            c.get('expected_counts') != held['expected_counts'] or
            c.get('qualification') != held['qualification'] or
            not c['qualification'] or any(v is not False for v in c['qualification'].values()) or
            digest(Path(sys.executable).resolve()) != c.get('python_executable_sha256')):
        raise ValueError('Only the exact fixed stage-local continuity audit is prepared')
    for name, value in pins.items():
        p = Path(name)
        if (p.is_absolute() or '..' in p.parts or not (ROOT/p).resolve().is_relative_to(ROOT) or
                not (ROOT/p).is_file() or (ROOT/p).is_symlink() or digest(ROOT/p) != value):
            raise ValueError('Bound source/input drift')
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError('Fresh fixed output required; prior partial evidence preserved')
    return c, pins


def audit(path, expected):
    c, pins = validate(path, expected)
    global np, patch_topology
    import numpy as np
    if np.__version__ != c.get('numpy_version'):
        raise ValueError('Reviewed NumPy version required')
    from patch_helpers import patch_topology
    OUTPUT.mkdir(exist_ok=False)
    report = dict(status='failed_or_rejected_stage_local_continuity', qualification=c['qualification'])
    try:
        authority = json.loads((ROOT/FILES['region_authority']).read_text())
        cap = json.loads((ROOT/FILES['cap_authority']).read_text())
        assembly = json.loads((ROOT/FILES['assembly']).read_text())
        groups = authority['exact_seed_incident_patch_components']
        if (len(groups) != 1 or authority['source_candidate_sha256'] != pins[FILES['before']] or
                cap['source_candidate_sha256'] != pins[FILES['before']] or len(cap['cap']['components']) != 1):
            raise ValueError('Exact original single-region/cap authority required')
        region = groups[0]; ids = np.asarray(region['face_ids'], dtype='<u8')
        component = cap['cap']['components'][0]
        fixed = np.asarray(component['exterior_face_ids'], dtype='<u8')
        if (len(ids) != authority['exact_incident_faces'] or len(ids) != 9872 or len(fixed) != 38 or
                set(component['incident_patch_face_ids']) != set(region['face_ids']) & set(component['face_ids']) or
                set(component['face_ids']) != set(component['incident_patch_face_ids']) | set(fixed.tolist())):
            raise ValueError('Complete9872 region and38 exterior cap cells required')
        p, f = read(ROOT/FILES['before']); q, g = read(ROOT/FILES['after'])
        if [len(p), len(f), len(q), len(g)] != c['expected_counts']:
            raise ValueError('Complete source/candidate counts changed')
        origins = np.fromfile(ROOT/FILES['coordinate_origins'], dtype='<u8')
        sources = np.fromfile(ROOT/FILES['face_sources'], dtype='<u8')
        cap_ids = np.fromfile(ROOT/FILES['candidate_cap_faces'], dtype='<u8')
        if (len(cap_ids) != assembly['inserted_cap_faces'] or len(np.unique(cap_ids)) != len(cap_ids) or
                (len(cap_ids) and cap_ids.max() >= len(g)) or
                not np.isin(np.flatnonzero(sources == MAX), cap_ids).all()):
            raise ValueError('Every new face must belong to the bound cap assembly')
        result = compare_region(p, f, q, g, ids, origins, sources, fixed)
        observed = result['before']; frozen = region['topology']
        cycles = frozen['oriented_boundary_cycles']
        frozen_edges = np.asarray([(cycle[i], cycle[(i+1) % len(cycle)])
                                   for cycle in cycles for i in range(len(cycle))], dtype='<u8')
        if (any(observed[key] != frozen[key] for key in ['vertices', 'edges', 'faces']) or
                observed['components'] != frozen['edge_connected_components'] or
                observed['euler_characteristic'] != frozen['Euler'] or
                observed['boundary_loops'] != len(cycles) or
                result['original_region_mask_sha256'] != authority['exact_incident_mask_sha256'] or
                result['exact_original_exterior_rows_sha256'] != authority['exterior_oriented_index_rows_sha256'] or
                result['original_oriented_boundary_ID_sha256'] != array_sha(sorted_directed_edges(frozen_edges)) or
                result['original_boundary_coordinate_rows_sha256'] != region['exact_boundary_coordinate_rows_sha256'] or
                not np.isin(result['fixed_candidate_cap_face_ids'], cap_ids).all()):
            raise ValueError('Measured original region/exterior/boundary does not reproduce frozen authority')
        report.update(status='stage_local_region_topology_and_exact_exterior_boundary_passed',
            result=result, region_authority_sha256=digest(ROOT/FILES['region_authority']),
            old_region_count_inherited_from_exact_authority=True, component_Euler_loops_measured_not_assumed_disks=True,
            semantic_channel_or_OEM_continuity_proved=False, geometry_export_calls=0)
    except Exception as exc:
        report['error'] = type(exc).__name__+': '+str(exc)
    unchanged = digest(path) == expected and all(digest(ROOT/n) == v for n, v in pins.items())
    report.update(contract_sha256=expected, source_sha256=digest(HERE), input_sha256=pins,
                  all_bound_inputs_unchanged=unchanged, whole_head_geometry_or_distance_admission=False)
    if not unchanged:
        report['status'] = 'failed_bound_input_drift'
    with (OUTPUT/'report.json').open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    return 0 if report['status'] == 'stage_local_region_topology_and_exact_exterior_boundary_passed' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(audit(args.contract.resolve(), args.contract_sha256))
