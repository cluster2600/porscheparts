"""Construct both halves of admitted source triangles without adding missing surfaces."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def rational(point):
    return tuple(F.from_float(float(x)) for x in point)


def value(point, plane):
    return sum((a*b for a, b in zip(point, plane[:3])), plane[3])


def intersection(a, b, plane):
    da, db = value(a, plane), value(b, plane)
    assert da*db < 0
    t = da/(da-db)
    return tuple(a[j] + t*(b[j]-a[j]) for j in range(3))


def clip(triangle, signs, edge_node, side):
    """Sutherland-Hodgman on original edges; indices retain source winding."""
    result = []
    for a, b in zip(triangle, triangle[1:]+triangle[:1]):
        inside_a, inside_b = signs[a]*side > 0, signs[b]*side > 0
        if inside_a != inside_b:
            result.append(edge_node[tuple(sorted((a, b)))])
        if inside_b:
            result.append(b)
    assert len(result) in (3, 4) and len(set(result)) == len(result)
    return [(result[0], result[i], result[i+1]) for i in range(1, len(result)-1)]


def controls():
    plane = tuple(map(F, (0, 0, 1, 0)))
    points = [(F(0), F(0), F(-1)), (F(2), F(0), F(1)), (F(0), F(2), F(1))]
    assert intersection(points[0], points[1], plane) == (F(1), F(0), F(0))
    assert intersection(points[0], points[2], plane) == (F(0), F(1), F(0))
    signs = {0:-1, 1:1, 2:1};edges = {(0,1):3, (0,2):4}
    assert len(clip([0,1,2], signs, edges, -1)) == 1
    assert len(clip([0,1,2], signs, edges, 1)) == 2
    try:
        intersection(points[1], points[2], plane)
    except AssertionError:
        pass
    else:
        raise AssertionError('Uncrossed original edge accepted')
    return dict(literal_rational_edge_intersections=True,one_and_two_triangle_halves=True,
                uncrossed_edge_refused=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controls-only', action='store_true')
    args = parser.parse_args();job = json.loads(args.job.read_text())
    assert job['schema'] == '935-source-transition-cuts-1'
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False);started = time.monotonic()
    control = controls()
    if args.controls_only:
        (args.output/'report.json').write_text(json.dumps(dict(controls=control,source_sha256=sha(__file__)))+'\n')
        return
    with np.load(job['arrays'], allow_pickle=False) as data:
        source_vertices, source_faces = data['vertices'], data['triangles']
    planes = [rational(row['keep_negative_halfspace_coefficients'])
              for row in json.loads(Path(job['planes']).read_text())]
    admitted = json.loads(Path(job['admitted_regions']).read_text())
    regions = [];original_ids = set();cut_keys = set()
    for row in admitted['regions']:
        path = Path(job['admitted_regions']).parent/('private-region-'+str(row['region'])+'.npz')
        assert sha(path) == row['private_region_sha256']
        with np.load(path, allow_pickle=False) as data:
            parents = data['transition_source_face_ids'];codes = data['section_edge_codes']
        assert len(parents) == row['transition_faces'] == len(codes)
        regions.append((row, parents, codes))
        original_ids.update(map(int, source_faces[parents].ravel()))
        cut_keys.update((row['plane'], int(code)) for code in codes)
    original_ids = sorted(original_ids);cut_keys = sorted(cut_keys)
    node_source = original_ids + [-1]*len(cut_keys)
    node_edge = [-1]*len(original_ids) + [key[1] for key in cut_keys]
    node_plane = [-1]*len(original_ids) + [key[0] for key in cut_keys]
    lookup_source = {key:i for i,key in enumerate(original_ids)}
    lookup_cut = {key:len(original_ids)+i for i,key in enumerate(cut_keys)}
    exact = [rational(source_vertices[i]) for i in original_ids]
    for plane, code in cut_keys:
        a, b = divmod(code, len(source_vertices))
        exact.append(intersection(rational(source_vertices[a]), rational(source_vertices[b]), planes[plane]))
    points = np.array([list(map(float, p)) for p in exact])
    errors = [sum((F.from_float(float(v))-e)**2 for v,e in zip(p,q)) for p,q in zip(points,exact)]
    assert max(errors) <= F.from_float(1e-8)**2
    faces = [];parents = [];region_ids = [];sides = [];rows = []
    for row, source_ids, codes in regions:
        plane = row['plane'];counts = {-1:0, 1:0}
        local_edges = {tuple(sorted((lookup_source[int(a)],lookup_source[int(b)]))):lookup_cut[(plane,int(code))]
                       for code in codes for a,b in [divmod(int(code),len(source_vertices))]}
        for parent in source_ids:
            original = list(map(int, source_faces[parent]));tri = [lookup_source[i] for i in original]
            signs = {i:1 if value(exact[i],planes[plane])>0 else -1 for i in tri}
            assert all(value(exact[i],planes[plane]) != 0 for i in tri)
            for side in (-1, 1):
                half = clip(tri, signs, local_edges, side);counts[side] += len(half)
                faces.extend(half);parents.extend([int(parent)]*len(half))
                region_ids.extend([row['region']]*len(half));sides.extend([side]*len(half))
        rows.append(dict(region=row['region'],plane=plane,original_transition_triangles=len(source_ids),
                         retained_half_triangles=counts[-1],outward_half_triangles=counts[1]))
    assert len(faces) == 3*len(set(parents)) == 2178
    destination = args.output/'private-transition-fragments.npz'
    np.savez_compressed(destination,points=points,triangles=np.array(faces,dtype=np.int64),
                        source_vertex_ids=np.array(node_source,dtype=np.int64),
                        source_edge_codes=np.array(node_edge,dtype=np.int64),
                        node_plane_indices=np.array(node_plane,dtype=np.int16),
                        parent_source_face_ids=np.array(parents,dtype=np.int64),
                        triangle_regions=np.array(region_ids,dtype=np.int16),
                        triangle_halfspaces=np.array(sides,dtype=np.int8))
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__),job_sha256=sha(args.job),controls=control,
                  original_transition_triangles=len(set(parents)),derived_triangles=len(faces),
                  original_vertex_nodes=len(original_ids),constructed_edge_nodes=len(cut_keys),regions=rows,
                  maximum_once_rounded_endpoint_error_nominal_mm=float(max(errors))**.5,
                  private_fragments_sha256=sha(destination),added_caps_or_hidden_surfaces=False,
                  original_scan_modified=False,anatomical_identity_accepted=False,
                  full_bare_head_created=False,physical_acceptance=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(transition_triangles=len(set(parents)),derived_triangles=len(faces))),flush=True)


if __name__ == '__main__':
    main()
