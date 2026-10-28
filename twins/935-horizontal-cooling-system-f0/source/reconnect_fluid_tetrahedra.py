"""Try disjoint convex 2-to-3 flips without moving the retained CFD boundary."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

from import_conforming_volume import determinant, integer_points
from prepare_conforming_surface import sha
from run_reconstruction import fresh, save

FACE_NODES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
EDGE_NODES = np.array([[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]])


def face_rows(cells):
    return np.sort(cells[:, FACE_NODES].reshape(-1, 3), axis=1)


def incidence(cells):
    faces = face_rows(cells)
    order = np.lexsort(faces.T[::-1])
    sorted_faces = faces[order]
    starts = np.r_[0, np.flatnonzero(np.any(sorted_faces[1:] != sorted_faces[:-1], axis=1)) + 1]
    counts = np.diff(np.r_[starts, len(faces)])
    if np.any((counts != 1) & (counts != 2)):
        raise ValueError('Manifold tetrahedral face incidence required')
    owners = np.full((len(starts), 2), -1, dtype=np.int64)
    owners[:, 0] = order[starts] // 4
    owners[counts == 2, 1] = order[starts[counts == 2] + 1] // 4
    ids = np.empty(len(faces), dtype=np.int64)
    ids[order] = np.repeat(np.arange(len(starts)), counts)
    return sorted_faces[starts], owners, ids.reshape(-1, 4)


def outer_faces(cells):
    rows, counts = np.unique(face_rows(cells), axis=0, return_counts=True)
    return rows[counts == 1]


def convex_flip(vertices, pair, shared):
    shared = tuple(map(int, shared))
    if len(set(shared)) != 3 or set(pair[0]) & set(pair[1]) != set(shared):
        raise ValueError('Exactly one shared face required')
    a, b, c = shared
    u, = set(map(int, pair[0])) - set(shared)
    v, = set(map(int, pair[1])) - set(shared)
    ids = sorted({a, b, c, u, v})
    if len(ids) != 5:
        raise ValueError('Five distinct vertices required')
    points, _ = integer_points(vertices[ids])
    lookup = dict(zip(ids, points))
    signed = lambda cell: determinant(*(lookup[int(i)] for i in cell))
    before = [signed(cell) for cell in pair]
    if min(before) <= 0:
        raise ValueError('Positive parent tetrahedra required')
    children = np.array([[u, v, a, b], [u, v, b, c], [u, v, c, a]], dtype=np.int64)
    values = [signed(cell) for cell in children]
    if all(value < 0 for value in values):
        children = children[:, [1, 0, 2, 3]]
        values = [-value for value in values]
    if min(values) <= 0:
        return None
    if sum(values) != sum(before) or not np.array_equal(outer_faces(pair), outer_faces(children)):
        raise ValueError('Exact local volume and complete outer boundary must agree')
    return children, (min(u, v), max(u, v))


def patch_quality(vertices, cells, outside, global_centres, global_volumes):
    centres = vertices[cells].mean(axis=1)
    t = vertices[cells]
    volumes = np.einsum('ij,ij->i', t[:, 1]-t[:, 0], np.cross(t[:, 2]-t[:, 0], t[:, 3]-t[:, 0])) / 6
    if np.any(volumes <= 0):
        raise ValueError('Positive local volume required')
    rows, owners, _ = incidence(cells)
    tensor = np.zeros((len(cells), 3, 3))
    sum_area = np.zeros(len(cells)); internal = np.zeros(len(cells), dtype=int)
    angles, weights, ratios = [], [], []
    for face, (left, right) in zip(rows, owners):
        xyz = vertices[face]; centre = xyz.mean(axis=0)
        area = np.cross(xyz[1]-xyz[0], xyz[2]-xyz[0]) / 2
        if right < 0:
            neighbour = outside[tuple(face)]
            if neighbour < 0:
                continue
            other_centre, other_volume = global_centres[neighbour], global_volumes[neighbour]
            local = [left]
        else:
            other_centre, other_volume = centres[right], volumes[right]
            local = [left, right]
        magnitude = np.linalg.norm(area)
        for index in local:
            tensor[index] += np.outer(area, area)
            sum_area[index] += magnitude; internal[index] += 1
        delta = other_centre - centres[left]
        cosine = abs(area @ delta) / (magnitude * np.linalg.norm(delta))
        angles.append(np.degrees(np.arccos(np.clip(cosine, 0, 1))))
        d1 = abs(area @ (centre-centres[left])); d2 = abs(area @ (other_centre-centre))
        weights.append(min(d1, d2) / (d1+d2))
        ratios.append(min(volumes[left], other_volume) / max(volumes[left], other_volume))
    average = np.divide(sum_area, internal, out=np.ones_like(sum_area), where=internal > 0)
    det = np.abs(np.linalg.det(tensor / average[:, None, None]**2))
    violations = [np.maximum((np.array(angles)-70)/20, 0),
                  np.maximum(1-np.array(weights)/.05, 0),
                  np.maximum(1-np.array(weights)/.02, 0),
                  np.maximum(1-np.array(ratios)/.01, 0), np.maximum(1-det/.001, 0)]
    return np.array([np.count_nonzero(x) for x in violations]), np.array([float(x @ x) for x in violations])


def improves(before, after):
    old_count, old_severity = before; new_count, new_severity = after
    return bool(new_count[-1] < old_count[-1] and np.all(new_count <= old_count)
                and np.all(new_severity <= old_severity + 1e-10))


def reconnect(vertices, cells):
    rows, owners, cell_faces = incidence(cells)
    boundary_count = (owners[cell_faces, 1] < 0).sum(axis=1)
    centres = vertices[cells].mean(axis=1)
    t = vertices[cells]
    volumes = np.einsum('ij,ij->i', t[:, 1]-t[:, 0], np.cross(t[:, 2]-t[:, 0], t[:, 3]-t[:, 0])) / 6
    if np.any(volumes <= 0):
        raise ValueError('Positive input cells required')
    edges = np.sort(cells[:, EDGE_NODES].reshape(-1, 2), axis=1)
    edge_keys = np.unique(edges[:, 0] * len(vertices) + edges[:, 1])
    reserved = np.zeros(len(cells), dtype=bool); removed = reserved.copy()
    added, decisions, locations = [], Counter(), []
    inserted_edges = set()
    for index in np.flatnonzero(boundary_count >= 2):
        if reserved[index]:
            decisions['reserved_source'] += 1; continue
        accepted = False
        for face_id in cell_faces[index]:
            if owners[face_id, 1] < 0:
                continue
            neighbour, = set(map(int, owners[face_id])) - {int(index)}
            pair_ids = np.array([index, neighbour]); pair = cells[pair_ids]
            face_ids = np.unique(cell_faces[pair_ids]); region = np.unique(owners[face_ids]); region = region[region >= 0]
            if reserved[region].any():
                decisions['reserved_neighbourhood'] += 1; continue
            proposal = convex_flip(vertices, pair, rows[face_id])
            if proposal is None:
                decisions['nonconvex_or_degenerate'] += 1; continue
            children, edge = proposal
            key = edge[0] * len(vertices) + edge[1]; position = np.searchsorted(edge_keys, key)
            if (position < len(edge_keys) and edge_keys[position] == key) or edge in inserted_edges:
                decisions['existing_edge'] += 1; continue
            outside = {}
            for fid in face_ids:
                if fid == face_id:
                    continue
                other = set(map(int, owners[fid])) - set(map(int, pair_ids))
                if len(other) != 1:
                    raise ValueError('Unique exterior neighbour required')
                outside[tuple(rows[fid])] = other.pop()
            before = patch_quality(vertices, pair, outside, centres, volumes)
            after = patch_quality(vertices, children, outside, centres, volumes)
            if not improves(before, after):
                decisions['FV_quality_not_monotone'] += 1; continue
            reserved[region] = True; removed[pair_ids] = True
            inserted_edges.add(edge); added.append(children); locations.append(centres[pair_ids].mean(axis=0))
            decisions['accepted_disjoint_patch'] += 1; accepted = True; break
        if not accepted:
            decisions['source_without_accepted_flip'] += 1
    output = np.vstack([cells[~removed], *added]) if added else cells.copy()
    assert len(output) == len(cells) + len(added)
    return output, {'input_cells':len(cells), 'output_cells':len(output),
                    'input_multi_boundary_cells':int((boundary_count >= 2).sum()),
                    'decision_counts':dict(decisions)}, np.asarray(locations).reshape(-1, 3)


def run(prepared, audited, output):
    prepared, audited = map(Path, (prepared, audited)); started = time.monotonic()
    proof = json.loads((audited/'assessment.json').read_text())
    reference = json.loads((prepared/'receipt.json').read_text())
    if (proof['volume_npz_sha256'] != sha(audited/'volume.npz')
            or proof['prepared_receipt_sha256'] != sha(prepared/'receipt.json')
            or not proof['complete_boundary_coordinate_triangle_marker_bijection']
            or not proof['exact_PLC_volume_equal'] or proof['exact_cell_orientation']['negative']
            or proof['exact_cell_orientation']['zero']):
        raise ValueError('Complete positive parent audit required')
    for name, digest in reference['output_sha256'].items():
        if sha(prepared/name) != digest:
            raise ValueError('Prepared boundary changed')
    z = np.load(audited/'volume.npz'); vertices = z['vertices']; cells = z['tetrahedra']
    if not 0 < len(cells) <= 2_000_000 or not 0 < len(vertices) <= 1_000_000:
        raise ValueError('Bounded study mesh required')
    out = fresh(output)
    result, report, centres = reconnect(vertices, cells)
    shutil.copyfile(prepared/'fluid.smesh', out/'fluid.smesh')
    for suffix, values, header, fmt in [
            ('node',vertices,f'{len(vertices)} 3 0 0',['%d','%.17g','%.17g','%.17g']),
            ('ele',result,f'{len(result)} 4 0','%d'),
            ('face',np.column_stack([z['boundary'],z['markers']]),f"{len(z['boundary'])} 1",'%d')]:
        with (out/f'fluid.1.{suffix}').open('x') as stream:
            stream.write(header+'\n'); np.savetxt(stream,np.column_stack([np.arange(len(values)),values]),fmt=fmt)
    np.savez_compressed(out/'reconnection-locations.npz', centres=centres)
    report.update(status='local_reconnections_pending_complete_volume_and_native_quality_audits',
                  source_sha256=sha(__file__),parent_assessment_sha256=sha(audited/'assessment.json'),
                  input_smesh_sha256=sha(prepared/'fluid.smesh'),input_file_unchanged=sha(out/'fluid.smesh')==sha(prepared/'fluid.smesh'),
                  vertex_coordinates_unchanged=True,exit=0,stop_reason=None,elapsed_s=time.monotonic()-started,
                  CFD_executed=False,CFD_accepted=False,manufacturing_authorized=False)
    save(out/'execution.json', report); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    run(*sys.argv[1:])
