"""Independently audit every admitted support exposure and its layer contacts.

The exact objects are triangle/plane intersections of the retained IEEE inputs.
Their binary64 encodings must be correctly rounded, without a geometry buffer.
Connectivity concerns exposed centerlines, not an assumed laser spot diameter.
"""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import time

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
import trimesh
from exact_contacts import clip_contacts, contact_encoding_check

SOURCE = Path(__file__).resolve().parent
CORE_SHA256 = '418482002d75e4b160f5837fdef91042fc63c3c1c85750a20d5359c53018e01f'
ADMISSIONS = ('envelopes', 'regions', 'skins', 'grids', 'contacts', 'collisions')
# CORE4184's centered 500 mm square, independently checked with the full params.
PLATE_DOMAIN = shapely.box(-250., -250., 250., 250.)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(segment):
    a, b = segment
    return (a, b) if a < b else (b, a)


def triangle_section(triangle, z):
    """Independent triangle clipping with exact barycentric edge weights.

    Unlike the hook's shared-edge interpolation, this clips each triangle from
    its three signed distances. Both definitions use the same retained inputs.
    """
    xyz = [tuple(Q(float(c)) for c in point) for point in triangle]
    height = Q(float(z))
    return clip_triangle(xyz, height)


def clip_triangle(xyz, height):
    distance = [point[2]-height for point in xyz]
    if all(d == 0 for d in distance):
        raise ValueError('Coplanar support triangle has no admitted centerline rule')
    cut = [xyz[i][:2] for i, d in enumerate(distance) if d == 0]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if distance[i]*distance[j] < 0:
            denominator = distance[j]-distance[i]
            cut.append(tuple((distance[j]*xyz[i][k]-distance[i]*xyz[j][k])/denominator
                             for k in (0, 1)))
    cut = list(dict.fromkeys(cut))
    if len(cut) < 2:
        return None
    if len(cut) != 2 or cut[0] == cut[1]:
        raise ValueError('Invalid or zero exact support section')
    return canonical(cut)


def encode(segment):
    return canonical(tuple(tuple(float(c) for c in p) for p in segment))


def orient(a, b, c):
    if a[0] == b[0]:
        return -(b[1]-a[1])*(c[0]-a[0])
    if a[1] == b[1]:
        return (b[0]-a[0])*(c[1]-a[1])
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def contains_point(segment, point):
    a, b = segment
    if a[0] == b[0]:
        return point[0] == a[0] and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    if a[1] == b[1]:
        return point[1] == a[1] and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
    return (orient(a, b, point) == 0 and
            all(min(a[k], b[k]) <= point[k] <= max(a[k], b[k]) for k in (0, 1)))


def segments_intersect(first, second):
    a, b = first
    c, d = second
    if a[1] == b[1] and c[0] == d[0]:
        return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(c[1], d[1]) <= a[1] <= max(c[1], d[1])
    if a[0] == b[0] and c[1] == d[1]:
        return min(c[0], d[0]) <= a[0] <= max(c[0], d[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
    signs = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (signs[0]*signs[1] < 0 and signs[2]*signs[3] < 0 or
            signs[0] == 0 and contains_point(first, c) or
            signs[1] == 0 and contains_point(first, d) or
            signs[2] == 0 and contains_point(second, a) or
            signs[3] == 0 and contains_point(second, b))


def outward(value, upper):
    result = float(value)
    if (upper and Q(result) < value) or (not upper and Q(result) > value):
        result = np.nextafter(result, math.inf if upper else -math.inf)
    return result


def boxes(segments):
    """Outward-rounded broad phase; exact predicates make the final decision."""
    return shapely.box(*np.asarray([[outward(min(a[0], b[0]), False),
        outward(min(a[1], b[1]), False), outward(max(a[0], b[0]), True),
        outward(max(a[1], b[1]), True)] for a, b in segments]).T)


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


def intersection_pairs(first, second=None):
    if not first or second is not None and not second:
        return []
    same = second is None
    second = first if same else second
    tree = shapely.STRtree(boxes(second))
    pairs = tree.query(boxes(first), predicate='intersects').T
    return [(int(a), int(b)) for a, b in pairs
            if (not same or a < b) and segments_intersect(first[a], second[b])]


def exact_sections(surfaces, z, prepared=None):
    """Convex triangle cuts certify whole segments, not just their endpoints."""
    sections = {}
    encodings = {}
    rounding_max = Q(0)
    rounding_ulp_max = Q(0)
    strict_mismatches = 0
    prepared = {} if prepared is None else prepared
    height = Q(float(z))
    for region, mesh in enumerate(surfaces):
        xyz = np.asarray(mesh.vertices)
        if region not in prepared:
            face_z = xyz[mesh.faces, 2]
            prepared[region] = (mesh, np.column_stack((face_z.min(axis=1), face_z.max(axis=1))), {})
        original, bounds, vertices = prepared[region]
        if original is not mesh:
            raise ValueError('Prepared section inputs changed')
        selected = np.flatnonzero((bounds[:, 0] <= z) & (bounds[:, 1] >= z))
        for face in selected:
            triangle = []
            for i in mesh.faces[face]:
                if int(i) not in vertices:
                    vertices[int(i)] = tuple(Q(float(c)) for c in xyz[i])
                triangle.append(vertices[int(i)])
            cut = clip_triangle(triangle, height)
            if cut is None:
                continue
            encoded = encode(cut)
            if encoded[0] == encoded[1]:
                raise ValueError('A nonzero exact segment collapses in float64')
            # Distinct rationals can necessarily round to the same floats.
            # Keep both exact identities; do not geometrically weld them.
            encodings.setdefault(encoded, set()).add(cut)
            record = sections.setdefault(cut, [])
            record.append((region, int(face)))
            for exact in cut:
                floating = tuple(float(q) for q in exact)
                for q, f in zip(exact, floating):
                    error = abs(q-Q(f))
                    rounding_max = max(rounding_max, error)
                    ulp = Q(math.ulp(f))
                    if error > ulp/2:
                        raise ValueError('Coordinate encoding exceeds nearest-even rounding bound')
                    rounding_ulp_max = max(rounding_ulp_max, error/ulp)
                if not contains_point(cut, tuple(Q(f) for f in floating)):
                    strict_mismatches += 1
    return sections, encodings, dict(exact_triangle_segments=sum(map(len, sections.values())),
        unique_rational_segments=len(sections), strict_encoded_endpoint_mismatches=strict_mismatches,
        distinct_rational_sections_sharing_one_encoding=sum(len(cuts)-1 for cuts in encodings.values()),
        encoding_error_ULP_max_upper=outward(rounding_ulp_max, True),
        encoding_error_Linf_mm_upper=outward(rounding_max, True))


def check_vectors(vectors, encodings):
    if (vectors.dtype != np.float64 or vectors.ndim != 3 or vectors.shape[1:] != (2, 2)
            or not np.isfinite(vectors).all()):
        raise ValueError('Support vectors must be finite float64 (N,2,2)')
    encoded = [canonical(tuple(tuple(float(c) for c in p) for p in segment)) for segment in vectors]
    zero = sum(a == b for a, b in encoded)
    duplicate = len(encoded)-len(set(encoded))
    actual, expected = set(encoded), set(encodings)
    extra, missing = actual-expected, expected-actual
    return dict(segments=len(encoded), zero_length_segments=zero, exact_duplicate_segments=duplicate,
        wrongly_encoded_or_outside_segments=len(extra), missing_material_section_segments=len(missing),
        first_extra_segment_mm=next(iter(extra), None), first_missing_segment_mm=next(iter(missing), None),
        correctly_rounded_whole_rational_sections=not extra and not missing,
        passed=not zero and not duplicate and not extra and not missing)


def pointer(value, reference):
    if not isinstance(reference, str) or not reference.startswith('/'):
        raise ValueError('Contact reference must be a relative JSON Pointer')
    for key in reference.split('/')[1:]:
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def contact_band_segments(group, kind, z, penetration):
    """Actual contact traces extended only by the declared vertical penetration."""
    height, depth = Q(float(z)), Q(float(penetration))
    result = []
    exact_key = '_exact_'+kind+'_contact_traces'
    paths = group.get(exact_key, group[kind+'_contact_traces_2d_mm'])
    for path in paths:
        points = path if exact_key in group else [tuple(Q(float(c)) for c in p) for p in path]
        for (t0, z0), (t1, z1) in zip(points[:-1], points[1:]):
            if t0 == t1:
                continue
            low, high = sorted((t0, t1))
            if z0 == z1:
                if abs(height-z0) > depth:
                    continue
            else:
                limits = sorted(t0+(h-z0)*(t1-t0)/(z1-z0) for h in (height-depth, height+depth))
                low, high = max(low, limits[0]), min(high, limits[1])
            if low < high:
                result.extend(map_interval(group, low, high))
    return result


def map_interval(group, low, high):
    if group['kind'] == 'grid':
        coordinate = Q(float(group['plane_coordinate_mm']))
        if group['fixed_axis'] == 0:
            return [((coordinate, low), (coordinate, high))]
        if group['fixed_axis'] == 1:
            return [((low, coordinate), (high, coordinate))]
        raise ValueError('Invalid grid fixed axis')
    result = []
    mapping = [tuple(Q(float(c)) for c in row) for row in group['mapping_t_xy_mm']]
    for a, b in zip(mapping[:-1], mapping[1:]):
        if b[0] <= a[0]:
            raise ValueError('Skin mapping is not strictly increasing')
        start, end = max(low, a[0]), min(high, b[0])
        if start < end:
            result.append(tuple(tuple(a[k]+(t-a[0])*(b[k]-a[k])/(b[0]-a[0])
                                      for k in (1, 2)) for t in (start, end)))
    return result


def positive_overlap(first, second):
    if any(orient(*first, p) != 0 for p in second):
        return False
    axis = 0 if first[0][0] != first[1][0] else 1
    return (max(min(p[axis] for p in first), min(p[axis] for p in second)) <
            min(max(p[axis] for p in first), max(p[axis] for p in second)))


def overlap_segment(first, second):
    if not positive_overlap(first, second):
        return None
    axis = 0 if first[0][0] != first[1][0] else 1
    low = max(min(p[axis] for p in first), min(p[axis] for p in second))
    high = min(max(p[axis] for p in first), max(p[axis] for p in second))
    a, b = first
    return tuple(tuple(a[k]+(t-a[axis])*(b[k]-a[k])/(b[axis]-a[axis]) for k in (0, 1))
                 for t in (low, high))


class ExposureGraph:
    """Streaming adjacent-layer centerline graph, preserving chronological anchors."""
    def __init__(self):
        self.previous = []
        self.previous_roots = []
        self.parent = []
        self.bottom = []
        self.top = []
        self.unanchored_layer_components = 0

    def root(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def join(self, a, b):
        a, b = self.root(a), self.root(b)
        if a != b:
            self.parent[b] = a
            self.bottom[a] |= self.bottom[b]
            self.top[a] |= self.top[b]

    def add(self, segments, bottom_contacts, upper_contacts):
        local = UnionFind(len(segments))
        for a, b in intersection_pairs(segments):
            local.join(a, b)
        roots = sorted({local.root(i) for i in range(len(segments))})
        ids = {}
        for r in roots:
            node = len(self.parent)
            self.parent.append(node)
            self.bottom.append(False)
            self.top.append(False)
            ids[r] = node
        nodes = [ids[local.root(i)] for i in range(len(segments))]
        for i, node in enumerate(nodes):
            self.bottom[node] |= i in bottom_contacts
            self.top[node] |= i in upper_contacts
        for a, b in intersection_pairs(segments, self.previous):
            self.join(nodes[a], self.previous_roots[b])
        self.unanchored_layer_components += sum(not self.bottom[self.root(node)] for node in ids.values())
        self.previous, self.previous_roots = segments, nodes
        return dict(layer_components=len(ids), unanchored_layer_components=sum(
            not self.bottom[self.root(node)] for node in ids.values()))

    def report(self):
        roots = sorted({self.root(i) for i in range(len(self.parent))})
        floating = sum(not self.bottom[r] for r in roots)
        no_upper = sum(not self.top[r] for r in roots)
        return dict(exposure_components=len(roots), components_without_lower_anchor=floating,
            components_without_upper_part_contact=no_upper,
            unanchored_layer_components=self.unanchored_layer_components,
            passed=bool(roots) and not floating and not no_upper and not self.unanchored_layer_components)


def verified_file(directory, name, expected):
    path = (directory/name).resolve()
    if not path.is_relative_to(directory) or not path.is_file() or sha(path) != expected:
        raise ValueError('Missing, escaped or changed process file: '+name)
    return path


def load_supports(directory, report, checkpoint, skin_remap=None):
    """Require sealed component identities; do not infer a release from a flag."""
    if (not report.get('manufacturing_preparation_admitted') or
            not checkpoint.get('manufacturing_preparation_admitted') or
            report['admission'] != checkpoint['admission']):
        raise ValueError('Six explicit support admissions are required')
    admissions = {}
    for name in ADMISSIONS:
        item = report['admission'][name]
        path = verified_file(directory, item['receipt'], item['receipt_sha256'])
        if report['outputs_sha256'].get(item['receipt']) != item['receipt_sha256']:
            raise ValueError('Admission is not in the process output identities')
        admission = json.loads(path.read_text())
        if (item['status'] != 'passed' or admission.get('status') != 'passed' or
                not admission.get('passed') or admission['input_sha256'] != report['input_sha256']):
            raise ValueError('Rejected or unrelated support admission: '+name)
        admissions[name] = admission
    if checkpoint['supports'] != report['supports'] or not checkpoint['supports']:
        raise ValueError('Process/checkpoint support descriptions disagree')
    surfaces, face_groups, groups = [], [], []
    for index, support in enumerate(report['supports']):
        if support['index'] != index:
            raise ValueError('Non-contiguous support region identities')
        for admission, field in (('skins', 'peripheral_skin'), ('grids', 'grid_coverage')):
            rows = admissions[admission]['regions']
            if (len(rows) != len(report['supports']) or rows[index]['region'] != index or
                    not rows[index]['passed'] or rows[index]['receipt'] != support[field]):
                raise ValueError('Support material differs from its sealed '+admission+' admission')
        path = directory/f'support-{index:03d}.npz'
        if (checkpoint['outputs_sha256'].get(path.name) != report['outputs_sha256'].get(path.name) or
                path.name not in report['outputs_sha256']):
            raise ValueError('Support mesh lacks a checkpoint/process SHA-256 identity')
        verified_file(directory, path.name, report['outputs_sha256'][path.name])
        with np.load(path, allow_pickle=False) as data:
            vertices, faces = data['vertices'], data['faces']
            order, kind = data['order'], data['type']
        if (vertices.dtype != np.float64 or not len(vertices) or not len(faces) or not np.isfinite(vertices).all() or
                faces.ndim != 2 or faces.shape[1] != 3 or faces.dtype.kind not in 'iu' or
                np.any(faces < 0) or np.any(faces >= len(vertices)) or
                len(faces) != support['faces'] or order.shape != (len(faces),) or kind.shape != order.shape):
            raise ValueError('Invalid retained support mesh')
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        if np.any(mesh.area_faces <= 0):
            raise ValueError('Zero-area support triangle')
        ownership = np.full(len(faces), -1, dtype=np.int64)
        material_groups = support['peripheral_skin']['support_surface_face_groups']
        if not material_groups or len({g['id'] for g in material_groups}) != len(material_groups):
            raise ValueError('Duplicate material component identity')
        rebuilt_skins = {}
        for group in material_groups:
            first, last = group['face_range']
            if (not 0 <= first < last <= len(faces) or np.any(ownership[first:last] != -1) or
                    not np.all(order[first:last] == group['order']) or
                    not np.all(kind[first:last] == group['type'])):
                raise ValueError('Support material face ranges overlap, escape or change scan attributes')
            contact = pointer(support, group['contact_reference'])
            if (contact.get('kind') != 'generated_material_component' or
                    group['component_geometry_sha256'] != contact['component_geometry_sha256']):
                raise ValueError('Material component/contact identity mismatch')
            for side in ('upper', 'lower'):
                name = side+'_contact_traces_2d_mm'
                source_name = side+'_interface_traces_2d_mm'
                if group[name] != contact[name] or group[source_name] != contact[source_name]:
                    raise ValueError('Contact traces differ from their sealed admission')
                for path_2d in group[name]:
                    a = np.asarray(path_2d)
                    if a.ndim != 2 or a.shape[1] != 2 or len(a) < 2 or not np.isfinite(a).all():
                        raise ValueError('Invalid material contact trace')
            wkb = bytes.fromhex(group['component_geometry_wkb_hex'])
            if hashlib.sha256(wkb).hexdigest() != group['component_geometry_sha256']:
                raise ValueError('Material component WKB identity mismatch')
            material = shapely.from_wkb(wkb)
            if material.is_empty or not material.is_valid or material.area <= 0:
                raise ValueError('Invalid admitted material component')
            # Necessary rational endpoints need not themselves be dyadic. Check
            # the whole exact trace and its correctly rounded encoding, rather
            # than asking GEOS whether a rounded boundary point is still inside.
            for side in ('upper', 'lower'):
                if not contact_encoding_check(material, group[side+'_interface_traces_2d_mm'],
                                               group[side+'_contact_traces_2d_mm']):
                    raise ValueError('Contact trace differs from its exact material/interface intersection encoding')
            exact_traces = {side: clip_contacts(material, group[side+'_interface_traces_2d_mm'])
                            for side in ('upper', 'lower')}
            triangles = mesh.triangles[first:last]
            if group['kind'] == 'grid':
                axis = group['fixed_axis']
                if axis not in (0, 1) or not np.all(triangles[:, :, axis] == group['plane_coordinate_mm']):
                    raise ValueError('Grid component faces leave their exact declared plane')
                polygons = shapely.polygons(triangles[:, :, [1-axis, 2]])
                if not np.all(shapely.covers(material, polygons)) or not shapely.union_all(polygons).equals(material):
                    raise ValueError('Grid triangles differ from the actual admitted material component')
            elif group['kind'] == 'skin':
                if skin_remap is None:
                    raise ValueError('Pinned skin remapping identity check is required')
                if group['order'] not in rebuilt_skins:
                    siblings = [g for g in material_groups if g['kind'] == 'skin' and g['order'] == group['order']]
                    siblings.sort(key=lambda g: g['face_range'][0])
                    if any(g['mapping_t_xy_mm'] != group['mapping_t_xy_mm'] for g in siblings):
                        raise ValueError('One skin order has incompatible coordinate mappings')
                    materials = [shapely.from_wkb(bytes.fromhex(g['component_geometry_wkb_hex'])) for g in siblings]
                    whole = materials[0] if len(materials) == 1 else shapely.MultiPolygon(materials)
                    rebuilt, mapping_receipt = skin_remap(whole, np.asarray(group['mapping_t_xy_mm'], dtype=float))
                    ranges = mapping_receipt['material_component_face_ranges']
                    if len(ranges) != len(siblings):
                        raise ValueError('Skin material remapping omitted a component')
                    rebuilt_skins[group['order']] = {}
                    for sibling, reference in zip(siblings, ranges):
                        if reference['component_geometry_sha256'] != sibling['component_geometry_sha256']:
                            raise ValueError('Skin material component ordering changed during reconstruction')
                        start, end = reference['face_range']
                        rebuilt_skins[group['order']][sibling['id']] = rebuilt.triangles[start:end]
                if not np.array_equal(triangles, rebuilt_skins[group['order']][group['id']]):
                    raise ValueError('Skin triangles differ from their admitted material/mapping')
            else:
                raise ValueError('Unknown support material kind')
            ownership[first:last] = len(groups)
            groups.append(dict(group, region=index,
                **{'_exact_'+side+'_contact_traces': traces for side, traces in exact_traces.items()}))
        if np.any(ownership < 0):
            raise ValueError('A support triangle has no admitted material component identity')
        surfaces.append(mesh)
        face_groups.append(ownership)
    return surfaces, face_groups, groups, admissions


def section_domain(points, offsets):
    if (points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all() or
            offsets.dtype.kind not in 'iu' or offsets.ndim != 1 or len(offsets) == 0 or
            offsets[0] != 0 or offsets[-1] != len(points) or np.any(np.diff(offsets) < 0)):
        raise ValueError('Invalid recorded part section')
    domain = shapely.GeometryCollection()
    for start, end in zip(offsets[:-1], offsets[1:]):
        ring = points[start:end]
        if len(ring) < 4 or not np.array_equal(ring[0], ring[-1]):
            raise ValueError('Open part boundary in support audit')
        polygon = Polygon(ring)
        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError('Invalid part boundary in support audit')
        domain = domain.symmetric_difference(polygon)
    if not domain.is_valid:
        raise ValueError('Invalid part contact domain')
    return domain


def contacts_at_layer(segments, sections, face_groups, groups, z, penetration, domain, layer):
    lower, upper, witnesses = set(), set(), []
    relevant = {g for owners in sections.values() for r, f in owners for g in [int(face_groups[r][f])]}
    bands = {i: {side: contact_band_segments(groups[i], side, z, penetration)
                 for side in ('lower', 'upper')} for i in relevant}
    for index, segment in enumerate(segments):
        owners = sorted({int(face_groups[r][f]) for r, f in sections[segment]})
        for owner in owners:
            group = groups[owner]
            for side in ('lower', 'upper'):
                hits = [overlap_segment(segment, trace) for trace in bands[owner][side]]
                hits = [hit for hit in hits if hit is not None]
                if not hits:
                    continue
                # Check the same piece of exposure against BOTH the contact
                # trace band and the part section, rather than borrowing a
                # remote part overlap elsewhere on a longer segment.
                part_length = sum(LineString([[float(c) for c in p] for p in hit]).intersection(domain).length
                                  for hit in hits)
                plate = False
                if layer == 0 and side == 'lower':
                    flat = [path for path in group['lower_contact_traces_2d_mm']
                            if all(float(p[1]) == 0 for p in path)]
                    plate_group = dict(group, lower_contact_traces_2d_mm=flat)
                    if '_exact_lower_contact_traces' in group:
                        plate_group['_exact_lower_contact_traces'] = [trace for trace in group['_exact_lower_contact_traces']
                            if all(p[1] == 0 for p in trace)]
                    overlaps = [overlap_segment(segment, trace) for trace in
                                contact_band_segments(plate_group, 'lower', z, penetration)]
                    plate = any(LineString([[float(c) for c in p] for p in overlap]).intersection(PLATE_DOMAIN).length > 0
                                for overlap in overlaps if overlap is not None)
                if part_length > 0 or plate:
                    (lower if side == 'lower' else upper).add(index)
                    witnesses.append(dict(segment=index, group=group['id'], region=group['region'], side=side,
                        anchor='plate_first_layer' if plate else 'positive_length_in_recorded_part_section',
                        part_overlap_length_mm=float(part_length)))
    return lower, upper, witnesses


def audit(directory, output, source_stl, part_cache=None):
    directory, output, source_stl = map(lambda p: Path(p).resolve(), (directory, output, source_stl))
    if output.exists():
        raise ValueError('Support audit output directory must be new')
    receipt_path = directory/'report.json'
    frozen = {receipt_path: sha(receipt_path), Path(__file__): sha(__file__)}
    report = json.loads(receipt_path.read_text())
    if (report['status'] != 'open_build_preparation_completed' or
            not report['source_and_runtime_unchanged_at_completion'] or
            report.get('immutable_core_sha256') != CORE_SHA256 or sha(source_stl) != report['input_sha256']):
        raise ValueError('Complete immutable same-input process report is required')
    frozen[source_stl] = report['input_sha256']
    required = ['support-stage.json', 'layers.csv', 'source/build_pyslm.py', 'source/admitted_regions.py',
                'source/peripheral_skins.py', 'source/grid_intervals.py', 'source/exact_regions.py',
                'source/prismatic_envelopes.py']
    if any(name not in report['outputs_sha256'] for name in required):
        raise ValueError('Process report omits a required geometry/source identity')
    for name, expected in report['outputs_sha256'].items():
        path = verified_file(directory, name, expected)
        frozen[path] = expected
    checkpoint = json.loads((directory/'support-stage.json').read_text())
    if (checkpoint['input_sha256'] != report['input_sha256'] or checkpoint['parameters'] != report['parameters'] or
            checkpoint['generator_source_sha256'] != CORE_SHA256):
        raise ValueError('Support checkpoint identity mismatch')
    # Reuse the sealed native-envelope validator from this run's source snapshot,
    # not a newer working copy. The part is reconstructed from the float64 input
    # pose; part-build.stl is only a float32 visualization and is not substituted.
    snapshot = directory/'source'
    if sha(snapshot/'build_pyslm.py') != CORE_SHA256:
        raise ValueError('The copied CORE source is not CORE4184')
    import pyslm
    import pyslm.support
    runtime_objects = [pyslm.Part, pyslm.support.BlockSupportGenerator,
        pyslm.support.GridBlockSupportGenerator, pyslm.support.GridBlockSupport,
        pyslm.support.utils.getOverhangMesh, pyslm.support.geometry.extrudeFace]
    for obj in runtime_objects:
        path = Path(inspect.getfile(obj))
        if sha(path) != report['runtime']['pyslm_source_files_sha256'].get(path.name):
            raise ValueError('Installed support source differs from the recorded process runtime')
    sys.path.insert(0, str(snapshot))
    spec = importlib.util.spec_from_file_location('support_audit_envelopes', snapshot/'admitted_regions.py')
    native = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(native)
        from peripheral_skins import remap
        if Path(inspect.getfile(remap)).resolve() != snapshot/'peripheral_skins.py':
            raise ValueError('Skin remapper was imported from another source snapshot')
    finally:
        sys.path.pop(0)
    surfaces, face_groups, groups, admissions = load_supports(directory, report, checkpoint, remap)
    store = native.EnvelopeStore(snapshot, report['input_sha256'], report['parameters'])
    if store.manifest_sha256 != admissions['envelopes']['store_manifest_sha256']:
        raise ValueError('Native envelope store and admission differ')
    cache_source = SOURCE.parent/'process-cache-20261016'
    sys.path.insert(0, str(cache_source))
    from part_cache import make_part, CachedLayers, core_module
    sys.path.pop(0)
    if report['parameters'] != core_module().PARAMETERS:
        raise ValueError('Full process parameters differ from the immutable study recipe')
    part = make_part(source_stl, report['parameters'])
    cache_binding = report['part_layer_cache']
    cache_path = Path(part_cache if part_cache is not None else cache_binding['directory']).resolve()
    cached = CachedLayers(cache_path, source_stl, report['parameters'])
    if (cached.report_sha256 != cache_binding['report_sha256'] or
            cached.report['n_layers'] != cache_binding['complete_cached_layers'] or
            cache_binding['consumed_layers'] != report['n_layers']):
        raise ValueError('Complete part cache binding differs from the process')
    if native.geometry_sha(part.geometry) != store.report['part_geometry_sha256']:
        raise ValueError('Support/part exact pose identity mismatch')
    for name in ('numpy', 'trimesh', 'shapely'):
        if importlib.metadata.version(name) != report['runtime']['packages'][name]:
            raise ValueError('Process/audit geometry runtime version mismatch')
    with (directory/'layers.csv').open() as stream:
        csv_rows = list(csv.DictReader(stream))
    height = report['parameters']['layer_height_mm']
    n = report['n_layers']
    if n != math.ceil(part.geometry.bounds[1, 2]/height) or len(csv_rows) != n:
        raise ValueError('Incomplete support exposure layer schedule')
    names = [f'layers/layer-{i:05d}.npz' for i in range(n)]
    actual = sorted(name for name in report['outputs_sha256'] if name.startswith('layers/') and name.endswith('.npz'))
    if actual != names:
        raise ValueError('Missing or surplus support layer identities')
    output.mkdir(parents=True)
    (output/'source').mkdir()
    for path in (Path(__file__), SOURCE/'exact_support_section.py', SOURCE/'exact_contacts.py'):
        shutil.copy2(path, output/'source'/path.name)
    started, rows, graph, encoded_graph = time.monotonic(), [], ExposureGraph(), ExposureGraph()
    prepared_sections = {}
    total_segments, max_error, strict_mismatches = 0, 0., 0
    source_files = {Path(__file__): sha(__file__), SOURCE/'exact_support_section.py': sha(SOURCE/'exact_support_section.py'),
                    SOURCE/'exact_contacts.py': sha(SOURCE/'exact_contacts.py'),
                    Path(inspect.getfile(trimesh.intersections)): sha(inspect.getfile(trimesh.intersections)),
                    Path(inspect.getfile(Q)): sha(inspect.getfile(Q))}
    for i, name in enumerate(names):
        z = (i+.5)*height
        expected_paths, _, _, expected_area = cached(part, z)
        expected_points = np.vstack(expected_paths) if expected_paths else np.empty((0, 2))
        expected_offsets = np.r_[0, np.cumsum([len(p) for p in expected_paths])].astype(np.int64)
        with np.load(directory/name, allow_pickle=False) as data:
            if float(data['z_mm']) != z or int(csv_rows[i]['layer']) != i or float(csv_rows[i]['z_mm']) != z:
                raise ValueError('Wrong support layer height/order')
            sections, encodings, geometry = exact_sections(surfaces, z, prepared_sections)
            vectors = check_vectors(data['support_scan_segments_mm'], encodings)
            if int(csv_rows[i]['support_scan_segments']) != vectors['segments']:
                raise ValueError('Support vector count differs from CSV')
            if (not np.array_equal(data['part_boundary_points_mm'], expected_points) or
                    not np.array_equal(data['part_boundary_offsets'], expected_offsets) or
                    float(csv_rows[i]['part_area_mm2']) != expected_area):
                raise ValueError('Support contact domain differs from the original complete part cache')
            length = float(np.linalg.norm(np.diff(data['support_scan_segments_mm'], axis=1), axis=2).sum())
            if float(csv_rows[i]['support_scan_length_mm']) != length:
                raise ValueError('Support exposure length differs from CSV')
            domain = section_domain(data['part_boundary_points_mm'], data['part_boundary_offsets'])
        segments = sorted(sections)
        if vectors['passed']:
            lower, upper, witnesses = contacts_at_layer(segments, sections, face_groups, groups, z,
                report['parameters']['support_teeth_upper_penetration_mm'], domain, i)
            connectivity = graph.add(segments, lower, upper)
            encoded_segments = [tuple(tuple(Q(float(c)) for c in p) for p in encoded)
                                for encoded in sorted(encodings)]
            indices = {cut: j for j, cut in enumerate(segments)}
            encoded_lower = {j for j, encoded in enumerate(sorted(encodings))
                             if any(indices[cut] in lower for cut in encodings[encoded])}
            encoded_upper = {j for j, encoded in enumerate(sorted(encodings))
                             if any(indices[cut] in upper for cut in encodings[encoded])}
            encoded_connectivity = encoded_graph.add(encoded_segments, encoded_lower, encoded_upper)
        else:
            # A mismatched vector must never borrow the expected section graph.
            witnesses = []
            connectivity = dict(layer_components=None, unanchored_layer_components=None, skipped_due_to_vector_failure=True)
            graph.previous, graph.previous_roots = [], []
            encoded_graph.previous, encoded_graph.previous_roots = [], []
            encoded_connectivity = dict(skipped_due_to_vector_failure=True)
        total_segments += vectors['segments']
        max_error = max(max_error, geometry['encoding_error_Linf_mm_upper'])
        strict_mismatches += geometry['strict_encoded_endpoint_mismatches']
        rows.append(dict(layer=i, z_mm=z, vectors=vectors, rational_confinement=geometry,
            connectivity=connectivity, encoded_connectivity=encoded_connectivity, contact_witnesses=witnesses))
        if i % 100 == 0:
            print(f'Support audit layer {i+1}/{n}', flush=True)
    store.verify()
    if cached.index != n:
        raise ValueError('Complete part contact cache was not consumed exactly once')
    if any(sha(p) != expected for p, expected in {**frozen, **source_files}.items()):
        raise ValueError('Source, receipt, native envelope or layer changed during support audit')
    if total_segments != report['support_scan_segments']:
        raise ValueError('Complete support segment count differs from process report')
    confinement = all(row['vectors']['passed'] for row in rows)
    connectivity = graph.report()
    encoded_connectivity = encoded_graph.report()
    connections_pass = connectivity['passed'] and encoded_connectivity['passed']
    result = dict(status='passed' if confinement and connections_pass else 'rejected',
        scope='all_recorded_support_centerlines_and_exposure_contacts', complete_build_audited=True,
        input_receipt_sha256=frozen[receipt_path], input_sha256=report['input_sha256'],
        layers_audited=n, support_scanpaths_audited=True, part_scanpaths_audited=False,
        geometric_confinement_passed=confinement, exposure_connectivity_passed=connections_pass,
        support_scan_segments=total_segments, exact_rational_section_confinement_passed=confinement,
        strict_binary64_endpoints_in_exact_sections=strict_mismatches == 0,
        strict_binary64_endpoint_mismatches=strict_mismatches,
        strict_binary64_endpoint_test_scope='Each endpoint against its own exact source-triangle cut.',
        correctly_rounded_coordinate_error_Linf_mm_upper=max_error,
        coordinate_error_scope='Necessary nearest-even float64 encoding of exact rational section endpoints; no domain buffer.',
        rational_exposure_graph=connectivity, encoded_exposure_graph=encoded_connectivity,
        rows=rows, audit_source_sha256=sha(__file__),
        audit_source_snapshot='source/audit_support_scanpaths.py',
        audit_dependencies_sha256={p.name: value for p, value in source_files.items()},
        native_admissions={name: report['admission'][name] for name in ADMISSIONS},
        part_cache_report_sha256=cached.report_sha256,
        runtime=dict(python=platform.python_version(), numpy=np.__version__, trimesh=trimesh.__version__,
            Shapely=shapely.__version__, GEOS=shapely.geos_version_string),
        criteria=dict(finite_nonzero_unique_segments=True, exact_correctly_rounded_section_encoding=True,
            geometric_buffer_mm=0, interlayer_rule='Exact XY intersection in consecutive exposed layers',
            intralayer_rule='Exact rational centerline intersection',
            chronological_lower_anchor_required_for_every_layer_component=True,
            lower_and_upper_contact_required_for_every_exposure_component=True,
            upper_contact_requires_positive_length_inside_recorded_part_section=True,
            section_tol_merge_used=False, laser_spot_width_assumed_mm=None),
        elapsed_seconds=time.monotonic()-started)
    (output/'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-stl', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path)
    args = parser.parse_args()
    result = audit(args.directory, args.output, args.source_stl, args.part_cache)
    print(json.dumps({key: result[key] for key in ('status', 'complete_build_audited', 'layers_audited',
        'geometric_confinement_passed', 'exposure_connectivity_passed')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
