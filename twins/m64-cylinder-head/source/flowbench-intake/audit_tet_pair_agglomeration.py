#!/usr/bin/env python3
"""Independent ASCII OpenFOAM tetra-pair union audit; no solver or quality waiver."""
import argparse
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import resource
import struct
import time

DOMAIN = 'fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
MANIFEST = '58b8be5aa0faeac678e6801cad29cfc5520cbf1590076276dbf5ad5157776aa1'
LOCALIZATION = '4eb33217f5610088af01e7c748c2bfa80bb297713b5e56954a89aad3b75fe0cc'
GEOMETRY_MANIFEST = 'ca5dbd6d9eae9960cdb1c04c8fbc06e71a958d60c0a5dee9c251a8b764d1ae01'
SOURCE_FILES = {
    'points': '28995ea4a7c4babb0ad163c5074e7d399f58d151b6f04e76cf1e7b8cc0da6e63',
    'faces': '526cc2694607e88987c98ec6a68be0d72571fefcf5960073270ebbcc860499fe',
    'owner': '8af322e5c36bf534de1625b48275383f2b3b89ff4e0cba9fb81ff69b1cdbfb46',
    'neighbour': '067acc378e09f241c04b95d22cf79059dcec131d46a42e167780aa638fdd43bd',
    'boundary': '2a354b6649bd0afc2b2df58069fc81f52ac4827db93a88a193e3d943e6026b16',
    'cellZones': '05e97c60237247c48d2c1d939e751cf559473d6452b2c3855fac7643ce934f1b',
}
MAPS = ('m64PointMap', 'm64FaceMap', 'm64CellMap', 'm64OldCellToNewCell')
WALL_GROUP_SOURCE = ('https://github.com/OpenFOAM/OpenFOAM-14/blob/'
                     '7b05503f98a85be88af930df48623b4d152bfc35/src/OpenFOAM/meshes/'
                     'polyMesh/polyPatches/derived/wall/wallPolyPatch.C#L54-L69')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def payload(path, classes):
    require(path.stat().st_size <= 256 * 1024 * 1024, 'bounded_ASCII_file_required')
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
    match = re.match(r'\s*FoamFile\s*\{([^{}]*)\}', text)
    require(match is not None and '#' not in text, 'plain_FOAM_header_required')
    header = dict(re.findall(r'(\w+)\s+([^;]+);', match[1]))
    require(header.get('format', '').strip() == 'ascii' and
            header.get('class', '').strip() in classes, 'ASCII_FOAM_class_mismatch')
    return text[match.end():].strip()


def counted(text):
    match = re.fullmatch(r'(\d+)\s*\((.*)\)\s*;?', text, flags=re.S)
    require(match is not None, 'counted_FOAM_list_required')
    return int(match[1]), match[2].strip()


def labels(path, classes=('labelList',)):
    count, content = counted(payload(path, classes))
    require(re.fullmatch(r'[\d\s+-]*', content) is not None, 'integer_labels_required')
    values = [int(x) for x in content.split()]
    require(len(values) == count, 'FOAM_label_count_mismatch')
    return values


def read_mesh(case):
    root = case / 'constant/polyMesh'
    count, content = counted(payload(root / 'points', ('vectorField',)))
    rows = re.findall(r'\(([^()]*)\)', content)
    require(len(rows) == count and not re.sub(r'\([^()]*\)', '', content).strip(), 'point_list_syntax')
    points = [tuple(float(x) for x in row.split()) for row in rows]
    require(all(len(p) == 3 and all(math.isfinite(x) for x in p) for p in points), 'finite_binary64_points_required')
    count, content = counted(payload(root / 'faces', ('faceList',)))
    rows = re.findall(r'(\d+)\s*\(([^()]*)\)', content)
    require(len(rows) == count and not re.sub(r'\d+\s*\([^()]*\)', '', content).strip(), 'face_list_syntax')
    faces = [tuple(map(int, row.split())) for _, row in rows]
    require(all(int(n) == len(f) == 3 and len(set(f)) == 3 and
                all(0 <= p < len(points) for p in f) for (n, _), f in zip(rows, faces)), 'triangular_face_contract')
    owner, neighbour = labels(root / 'owner'), labels(root / 'neighbour')
    require(len(owner) == len(faces) and 0 <= len(neighbour) < len(faces), 'face_addressing_sizes')
    ncell = max(owner + neighbour) + 1
    require(ncell > 0 and all(0 <= c < ncell for c in owner + neighbour), 'cell_label_range')
    require(all(owner[i] < n for i, n in enumerate(neighbour)), 'ordered_distinct_internal_cells')
    patches = []
    count, content = counted(payload(root / 'boundary', ('polyBoundaryMesh',)))
    blocks = re.findall(r'(\w+)\s*\{([^{}]*)\}', content)
    require(len(blocks) == count and not re.sub(r'\w+\s*\{[^{}]*\}', '', content).strip(), 'patch_dictionary_syntax')
    for name, body in blocks:
        entries = re.findall(r'(\w+)\s+([^;]+);', body)
        require(len(dict(entries)) == len(entries), 'duplicate_patch_field')
        fields = {key: ' '.join(value.split()) for key, value in entries}
        require(not re.sub(r'\w+\s+[^;]+;', '', body).strip(), 'unsupported_patch_dictionary')
        start, size = int(fields.pop('startFace')), int(fields.pop('nFaces'))
        patches.append((name, start, size, fields))
    require([p[0] for p in patches] == ['walls', 'receiver_outlet', 'inlet'], 'three_ordered_patches_required')
    require([p[3]['type'] for p in patches] == ['wall', 'patch', 'patch'], 'uncoupled_patch_types_required')
    cursor = len(neighbour)
    for _, start, size, _ in patches:
        require(start == cursor and size > 0, 'contiguous_nonempty_boundary_partition')
        cursor += size
    require(cursor == len(faces), 'complete_boundary_partition')
    count, content = counted(payload(root / 'cellZones', ('cellZoneList',)))
    zone = re.fullmatch(r'air\s*\{\s*(?:type\s+cellZone;\s*)?cellLabels\s+List<label>\s+(.*?)\s*;\s*\}', content, re.S)
    require(count == 1 and zone is not None, 'only_air_cell_zone_supported')
    number, body = counted(zone[1]); zone_cells = [int(x) for x in body.split()]
    require(number == len(zone_cells) == ncell and set(zone_cells) == set(range(ncell)), 'air_zone_must_cover_every_cell_once')
    for name, cls in (('pointZones', 'pointZoneList'), ('faceZones', 'faceZoneList')):
        if (root / name).exists():
            require(counted(payload(root / name, (cls,))) == (0, ''), 'unexpected_point_or_face_zone')
    return {'points': points, 'faces': faces, 'owner': owner, 'neighbour': neighbour,
            'cells': ncell, 'patches': patches, 'zone': zone_cells}


def canonical(face):
    return min(face, face[1:] + face[:1], face[2:] + face[:2])


def effective_patch_fields(fields):
    """Only exact type=wall receives the native wallPolyPatch default group."""
    result = dict(fields)
    if result.get('type') != 'wall':
        return result
    groups = set()
    if 'inGroups' in result:
        match = re.fullmatch(r'(?:List<word>\s*)?(\d+)?\s*\(([^()]*)\)', result.pop('inGroups'))
        require(match is not None, 'unsupported_wall_group_list')
        words = match[2].split()
        require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]*', x) for x in words) and
                len(words) == len(set(words)) and
                (match[1] is None or int(match[1]) == len(words)), 'invalid_wall_group_list')
        groups.update(words)
    # OpenFOAM-14 wallPolyPatch dictionary constructor appends wall if absent.
    # Extra groups remain significant; no other patch metadata is discarded.
    result['inGroups'] = tuple(sorted(groups | {'wall'}))
    return result


def determinant(a, b, c, d):
    u, v, w = [tuple(p[i] - a[i] for i in range(3)) for p in (b, c, d)]
    return (u[0] * (v[1]*w[2] - v[2]*w[1]) - u[1] * (v[0]*w[2] - v[2]*w[0])
            + u[2] * (v[0]*w[1] - v[1]*w[0]))


def incidences(mesh):
    result = [[] for _ in range(mesh['cells'])]
    for f, owner in enumerate(mesh['owner']):
        result[owner].append((f, 1))
        if f < len(mesh['neighbour']):
            result[mesh['neighbour'][f]].append((f, -1))
    return result


def audit(source, candidate, requested_faces, maps):
    """Reconstruct unions from source faceSet; producer maps are only claims."""
    pm, fm, cm, old_new = (maps[n] for n in MAPS)
    require(len(pm) == len(candidate['points']) == len(source['points']) and
            set(pm) == set(range(len(source['points']))), 'point_map_not_bijective')
    # OpenFOAM reads scalar=64. Seventeen-digit output may change decimal tokens
    # without changing their loaded binary64; compare bits, not rounded distances.
    require(all(struct.pack('!3d', *candidate['points'][i]) ==
                struct.pack('!3d', *source['points'][old]) for i, old in enumerate(pm)),
            'exact_point_binary64_coordinates_changed')
    require(requested_faces and len(requested_faces) == len(set(requested_faces)), 'nonempty_unique_requested_faces_required')
    groups = [{i} for i in range(source['cells'])]; used = set(); pairs = []
    for f in requested_faces:
        require(0 <= f < len(source['neighbour']), 'requested_face_must_be_internal')
        a, b = source['owner'][f], source['neighbour'][f]
        require(a != b and a not in used and b not in used, 'requested_pairs_must_be_disjoint')
        used.update((a, b)); groups[a] = groups[b] = {a, b}; pairs.append((f, a, b))
    require(len(cm) == candidate['cells'] == source['cells'] - len(pairs) and
            len(old_new) == source['cells'], 'cell_map_sizes')
    expected = [-1] * source['cells']; seen = set(); candidate_groups = []
    for new, old in enumerate(cm):
        require(0 <= old < source['cells'], 'new_to_old_cell_label_range')
        group = groups[old]; key = tuple(sorted(group))
        require(key not in seen, 'source_group_represented_twice')
        seen.add(key); candidate_groups.append(group)
        for parent in group:
            expected[parent] = new
    require(-1 not in expected and old_new == expected, 'old_to_new_cell_map_not_independently_reproduced')
    retained = set(range(len(source['faces']))) - set(requested_faces)
    require(len(fm) == len(candidate['faces']) == len(retained) and set(fm) == retained, 'face_map_must_remove_only_requested_faces')
    old_inc, new_inc = incidences(source), incidences(candidate)
    float_points = [tuple(map(float, p)) for p in source['points']]
    for rows in old_inc:
        nodes = set(itertools.chain.from_iterable(source['faces'][f] for f, _ in rows))
        require(len(rows) == 4 and len(nodes) == 4 and
                {tuple(sorted(source['faces'][f])) for f, _ in rows} == set(itertools.combinations(sorted(nodes), 3)), 'source_cell_not_a_tetrahedron')
        for f, sign in rows:
            face = source['faces'][f] if sign == 1 else source['faces'][f][::-1]
            opposite = next(iter(nodes - set(face)))
            value = determinant(*(float_points[p] for p in (*face, opposite)))
            require(math.isfinite(value) and value < 0, 'source_tetrahedron_not_positive_outward')
    for new, old in enumerate(fm):
        face = tuple(pm[p] for p in candidate['faces'][new])
        a = old_new[source['owner'][old]]
        b = old_new[source['neighbour'][old]] if old < len(source['neighbour']) else None
        ca = candidate['owner'][new]
        cb = candidate['neighbour'][new] if new < len(candidate['neighbour']) else None
        require(a != b, 'unremoved_internal_pair_face')
        if (ca, cb) == (a, b):
            require(canonical(face) == canonical(source['faces'][old]), 'retained_face_orientation_changed')
        else:
            require(b is not None and (ca, cb) == (b, a) and
                    canonical(face) == canonical(source['faces'][old][::-1]), 'face_addressing_or_flip_inconsistent')
    for before, after in zip(source['patches'], candidate['patches']):
        name, start, count, fields = before; new_name, new_start, new_count, new_fields = after
        require((name, count, effective_patch_fields(fields)) ==
                (new_name, new_count, effective_patch_fields(new_fields)) and
                set(fm[new_start:new_start+new_count]) == set(range(start, start+count)), 'patch_label_metadata_or_membership_changed')
    require({old_new[c] for c in source['zone']} == set(candidate['zone']), 'cell_zone_not_exactly_mapped')
    removed = set(requested_faces)
    for new, group in enumerate(candidate_groups):
        expected_faces = {f for parent in group for f, _ in old_inc[parent]} - removed
        require({fm[f] for f, _ in new_inc[new]} == expected_faces and
                len(new_inc[new]) == (6 if len(group) == 2 else 4), 'cell_boundary_not_exact_union_of_parents')
    rational = {}
    def point(p):
        if p not in rational:
            rational[p] = tuple(Fraction.from_float(x) for x in source['points'][p])
        return rational[p]
    for f, a, b in pairs:
        face = source['faces'][f]
        opposite = [next(iter({p for fid, _ in old_inc[c] for p in source['faces'][fid]} - set(face))) for c in (a, b)]
        da, db = [determinant(*(point(p) for p in (*face, q))) for q in opposite]
        require(da < 0 < db, 'paired_tetrahedra_not_on_opposite_sides_exactly')
        volume = (db - da) / 6; surface_volume = Fraction(0)
        for fid, sign in new_inc[old_new[a]]:
            tri = tuple(pm[p] for p in candidate['faces'][fid])
            if sign < 0:
                tri = tri[::-1]
            surface_volume += determinant((0, 0, 0), *(point(p) for p in tri)) / 6
        require(surface_volume == volume > 0, 'polyhedron_volume_not_exact_sum_of_parents')
    return {'paired_cells': len(pairs), 'source_cells': source['cells'], 'candidate_cells': candidate['cells'],
            'unchanged_singleton_cells': source['cells'] - 2*len(pairs), 'source_points': len(pm),
            'retained_faces': len(fm), 'removed_internal_faces': len(pairs),
            'boundary_triangles': len(source['faces']) - len(source['neighbour']),
            'point_coordinates_bit_exact_binary64': True, 'decimal_token_identity_claimed': False,
            'rational_coordinate_basis': 'exact_rationals_of_loaded_binary64_values',
            'maps_independently_reproduced': True,
            'patch_groups_compared_as_native_wall_default_union_only': True,
            'patch_group_semantics_source': WALL_GROUP_SOURCE,
            'all_retained_triangles_and_patch_membership_preserved': True,
            'each_pair_has_exact_six_face_union': True, 'parent_sets_disjoint_and_exhaustive': True,
            'exact_rational_pair_volumes_and_total_conservation_by_partition': True,
            'global_source_self_intersection_absence_proven': False,
            'multiple_faces_between_cells_allowed_if_exactly_inherited': True}


def run(args):
    started = time.monotonic(); output = args.output.resolve()
    require(not output.exists(), 'output_must_be_new')
    source_root = args.source_case / 'constant/polyMesh'
    paths = {source_root / n: h for n, h in SOURCE_FILES.items()}
    paths.update({args.manifest: MANIFEST, args.localization / 'localization-receipt.json': LOCALIZATION,
                  args.localization / 'remote-output/copy-geometry-before.sha256': GEOMETRY_MANIFEST,
                  args.face_set: args.face_set_sha256, Path(__file__): sha(__file__)})
    require(re.fullmatch(r'[0-9a-f]{64}', args.face_set_sha256) is not None, 'requested_face_set_hash_required')
    require(all(sha(p) == h for p, h in paths.items()), 'pinned_source_or_request_hash_mismatch')
    manifest = json.loads(args.manifest.read_text())
    require(manifest['exports']['domain_brep']['sha256'] == DOMAIN, 'unified_domain_manifest_required')
    candidate_files = [args.candidate_case / 'constant/polyMesh' / n for n in SOURCE_FILES]
    candidate_files += [args.candidate_case / 'agglomerationMaps' / n for n in MAPS]
    for case in (args.source_case, args.candidate_case):
        candidate_files += [case / 'constant/polyMesh' / n for n in ('pointZones', 'faceZones')
                            if (case / 'constant/polyMesh' / n).exists()]
    paths.update({p: sha(p) for p in candidate_files})
    report = {'schema': 'm64-private-tet-pair-agglomeration-review/v1', 'status': 'rejected_or_incomplete',
              'native_domain_sha256': DOMAIN, 'inputs_sha256': {str(p): h for p, h in paths.items()},
              'approved_for_mesh_diagnostic': False, 'solver_execution_authorized': False,
              'CFD_executed': False, 'CFD_qualified': False, 'manufacturing_authorized': False,
              'cell_zone_authority': 'air_cellZone_not_residual_topoSets',
              'residual_topoSets_remapping_audited': False, 'solver_fields_audited': False}
    try:
        source, candidate = read_mesh(args.source_case), read_mesh(args.candidate_case)
        maps = {n: labels(args.candidate_case / 'agglomerationMaps' / n) for n in MAPS}
        report['independent_transformation_audit'] = audit(source, candidate, labels(args.face_set, ('faceSet',)), maps)
        report['status'] = 'transformation_verified_checkMesh_only'
        report['approved_for_mesh_diagnostic'] = True
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    report['all_inputs_unchanged'] = all(sha(p) == h for p, h in paths.items())
    if not report['all_inputs_unchanged']:
        report.update(status='inputs_changed_rejected', approved_for_mesh_diagnostic=False)
    report['elapsed_seconds'] = time.monotonic() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    output.chmod(0o600)
    print(json.dumps({k: report[k] for k in ('status', 'approved_for_mesh_diagnostic', 'elapsed_seconds')}))
    return 0 if report['approved_for_mesh_diagnostic'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-case', 'candidate-case', 'face-set', 'manifest', 'localization', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--face-set-sha256', required=True)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    raise SystemExit(run(parser.parse_args()))
