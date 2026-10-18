"""Positive intersections of actual IEEE support triangles, with exact witnesses."""
from fractions import Fraction as Q
import hashlib
from pathlib import Path
import sys
import time

import numpy as np
import trimesh

CLASSIFIER = Path(__file__).resolve().with_name('classify_mesh_contacts.py')
if not CLASSIFIER.is_file():
    CLASSIFIER = CLASSIFIER.parent.parent / 'design-20261016/classify_mesh_contacts.py'
sys.path.insert(0, str(CLASSIFIER.parent))
from classify_mesh_contacts import intersection, subtract, dot, cross


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def root(self, value):
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def join(self, a, b):
        a, b = self.root(a), self.root(b)
        if a != b:
            self.parent[b] = a


def ratio(value):
    return [str(value.numerator), str(value.denominator)]


def connected_material(vertices, faces, groups):
    """Certify a spanning forest; point contacts never connect two sheets.

    Interface attributes retain the caller's contact representation/provenance.
    The separately required exposure audit checks actual sampled layers too.
    """
    started = time.monotonic()
    frozen = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (Path(__file__).resolve(), CLASSIFIER)}
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    if (vertices.dtype != np.float64 or vertices.ndim != 2 or vertices.shape[1] != 3
            or not np.isfinite(vertices).all() or faces.ndim != 2 or faces.shape[1] != 3
            or not np.issubdtype(faces.dtype, np.integer) or not len(faces)
            or faces.min() < 0 or faces.max() >= len(vertices) or not groups):
        raise ValueError('Finite float64 vertices and nonempty indexed triangles/groups are required')
    cursor = 0
    identities = set()
    for group in groups:
        begin, end = group['face_range']
        if begin != cursor or not begin < end <= len(faces) or group['id'] in identities:
            raise ValueError('Unique ordered material groups must partition every actual face')
        for name in ('upper_contact_trace_mm', 'lower_contact_trace_mm'):
            if not np.isfinite(group[name]) or group[name] < 0:
                raise ValueError('Contact measures must be finite and nonnegative')
        cursor = end
        identities.add(group['id'])
    if cursor != len(faces):
        raise ValueError('Material groups omitted actual faces')

    triangles = vertices[faces]
    bounds = np.concatenate((triangles.min(axis=1), triangles.max(axis=1)), axis=1)
    exact_vertices, trees = {}, {}
    tested = 0

    def triangle(index):
        result = []
        for vertex in faces[index]:
            key = int(vertex)
            if key not in exact_vertices:
                exact_vertices[key] = tuple(Q(float(c)) for c in vertices[key])
            result.append(exact_vertices[key])
        return tuple(result)

    # A conservative absolute roundoff bound certifies ordinary nonzero areas;
    # uncertain/underflow/overflow cases use exact input rationals instead.
    magnitude = np.max(np.abs(triangles), axis=(1, 2))
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        bound = 32*np.finfo(float).eps*magnitude*magnitude
    safe = ((magnitude >= 2.**-400) & (magnitude <= 2.**400)
            & np.isfinite(normals).all(axis=1) & (np.max(np.abs(normals), axis=1) > bound))
    uncertain = np.flatnonzero(~safe)
    for index in uncertain:
        a, b, c = triangle(int(index))
        if not any(cross(subtract(b, a), subtract(c, a))):
            raise ValueError('An actual support triangle has exact zero area')

    def overlap(a, b):
        return bool(np.all(a[:3] <= b[3:]) and np.all(b[:3] <= a[3:]))

    def bridge(first, second, allow_coplanar_edge=False):
        nonlocal tested
        box = np.r_[bounds[second, :3].min(axis=0), bounds[second, 3:].max(axis=0)]
        selected = first[np.all(bounds[first, :3] <= box[3:], axis=1)
                         & np.all(bounds[first, 3:] >= box[:3], axis=1)]
        if not len(selected):
            return None
        key = (int(second[0]), int(second[-1]), len(second))
        if key not in trees:
            trees[key] = trimesh.util.bounds_tree(bounds[second])
        tree = trees[key]
        for a in selected:
            for local_b in tree.intersection(bounds[a]):
                b = int(second[local_b])
                report = intersection(triangle(int(a)), triangle(b))
                tested += 1
                points = report['points']
                area = report.get('projected_area', Q(0))
                length2 = max((dot(subtract(p, q), subtract(p, q))
                               for p in points for q in points), default=Q(0))
                coplanar = 'projection_axis' in report
                positive = area > 0 or (length2 > 0 and (not coplanar or allow_coplanar_edge))
                if positive:
                    return dict(face_pair=[int(a), b], kind=report['kind'],
                        projection_axis=report.get('projection_axis'),
                        projected_area_mm2_exact_ratio=ratio(area),
                        squared_extent_in_report_coordinates_exact_ratio=ratio(length2),
                        intersection_points_exact_ratios=[[ratio(c) for c in p] for p in points])
        return None

    # Exact coordinate equality only; no welding radius or change to the mesh.
    _, inverse = np.unique(vertices, axis=0, return_inverse=True)
    adjacency = trimesh.graph.face_adjacency(faces=inverse[faces])
    face_union = UnionFind(len(faces))
    owner = np.empty(len(faces), dtype=np.int64)
    for index, group in enumerate(groups):
        owner[slice(*group['face_range'])] = index
    for a, b in adjacency:
        if owner[a] == owner[b]:
            face_union.join(int(a), int(b))
    internal, group_faces, group_bounds = [], [], []
    for index, group in enumerate(groups):
        selected = np.arange(*group['face_range'])
        pieces = {}
        for face in selected:
            pieces.setdefault(face_union.root(int(face)), []).append(int(face))
        pieces = [np.asarray(piece, dtype=np.int64) for piece in pieces.values()]
        joined = UnionFind(len(pieces))
        witnesses = []
        for a in range(len(pieces)):
            for b in range(a+1, len(pieces)):
                if joined.root(a) == joined.root(b):
                    continue
                witness = bridge(pieces[a], pieces[b], allow_coplanar_edge=True)
                if witness:
                    joined.join(a, b)
                    witnesses.append(witness)
        components = len({joined.root(i) for i in range(len(pieces))})
        internal.append(dict(group_id=group['id'], indexed_edge_components=len(pieces),
                             positive_intersection_witnesses=witnesses,
                             remaining_components=components, passed=components == 1))
        group_faces.append(selected)
        group_bounds.append(np.r_[bounds[selected, :3].min(axis=0), bounds[selected, 3:].max(axis=0)])

    joined = UnionFind(len(groups))
    witnesses = []
    for a in range(len(groups)):
        for b in range(a+1, len(groups)):
            if joined.root(a) == joined.root(b) or not overlap(group_bounds[a], group_bounds[b]):
                continue
            witness = bridge(group_faces[a], group_faces[b])
            if witness:
                joined.join(a, b)
                witnesses.append(dict(group_ids=[groups[a]['id'], groups[b]['id']], **witness))
    components = {}
    for i, group in enumerate(groups):
        components.setdefault(joined.root(i), []).append(i)
    components = [dict(group_ids=[groups[i]['id'] for i in indices],
        upper_contact_group_ids=[groups[i]['id'] for i in indices if groups[i]['upper_contact_trace_mm'] > 0],
        lower_contact_group_ids=[groups[i]['id'] for i in indices if groups[i]['lower_contact_trace_mm'] > 0])
        for indices in components.values()]
    for component in components:
        component['passed'] = bool(component['upper_contact_group_ids'] and component['lower_contact_group_ids'])
    passed = all(row['passed'] for row in internal + components)
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected
           for path, expected in frozen.items()):
        raise ValueError('Material connection source changed during its execution')
    return dict(status='passed' if passed else 'rejected',
        representation='Actual retained IEEE float64 triangles; exact rational intersections; spanning witness forest.',
        contact_scope='Caller-supplied interface contact identities; requires independent complete exposure audit.',
        source_sha256=frozen[str(Path(__file__).resolve())],
        classifier_sha256=frozen[str(CLASSIFIER)],
        input_geometry_sha256=hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest(),
        groups=len(groups), faces=len(faces), internal_connectivity=internal,
        exact_degeneracy_fallbacks=len(uncertain),
        positive_intersection_witnesses=witnesses, components=components,
        exact_triangle_pairs_tested=tested, seconds=time.monotonic()-started)
