#!/usr/bin/env python3
"""Package the one reviewed native 37/38/40 surface union, without new physics.

The reference is the explicitly audited OCCT serialization control, not raw
bitwise geometric descriptor identity with the earlier BRep. Existing neck and
guide-communication evidence is inherited, never recomputed by this exporter.
All geometry and detailed receipts belong in a private output directory.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import resource
import shutil
import time

OLD = '7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
NEW = 'fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
MANIFEST = '92576714217042c0f152c1da7d8a8fa0da8f1757e5ec06c9c6f4eee3c66ccc58'
REVIEW = '7bd9c92d5ac4bafc0146cb77e55f8e95c45d041972ad235f2dce0ab84a21b897'
REVIEW_SOURCE = '6ae2439a80c7469579325eb4e191729baa3bce1e0b5da97bc0dd8592baf648b6'
NOOP = 'cf81801a4fb103d429503752f5433b0474b5268d0941134afd693c7225a0f71e'
GROUP = {37, 38, 40}
CLEAN_BOP = {'has_faulty': False, 'has_errors': False, 'has_warnings': False, 'faults': []}
ROLES = {'inlet', 'receiver_outlet', 'walls_port', 'walls_chamber', 'walls_seat',
         'walls_valve', 'walls_guide', 'walls_receiver', 'fixture_stem_seals'}
REVIEW_GATES = (
    'native_valid', 'candidate_BOP_clean', 'three_to_one_faces', 'one_solid_one_shell',
    'all_85_other_faces_exact_support_contours_pcurves_tolerance', 'exact_merged_support',
    'same_face_orientation', 'exact_external_oriented_boundary', 'external_pcurves_exact',
    'all_remaining_occurrences_including_seam_pcurves_exact',
    'only_four_authorized_edges_removed_all_others_exact',
    'no_new_vertex_coordinates_or_increased_vertex_tolerances',
    'remaining_vertices_exact_multiset_subset', 'merged_face_tolerance_not_increased',
    'vertices_120_to_118_with_exact_retained_edge_incidence',
    'control_matches_existing_noop_native_descriptors_exactly',
    'control_preserves_all_edge_non_curve_fields',
    'control_preserves_face_orientations_and_tolerances',
    'control_preserves_all_occurrence_orientations_and_ranges',
    'control_preserves_vertices_exactly', 'control_preserves_topology_counts',
    'inputs_and_audit_source_unchanged')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def content_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def reviewed_face_relation(review):
    """Fail closed on the exact reviewed many-to-one relation, not face counts."""
    if (review.get('schema') != 'm64-private-independent-three-face-native-merge-control-audit/v2'
            or review.get('status') != 'native_merge_matches_serialization_control_exactly'
            or review.get('original_sha256') != OLD or review.get('candidate_sha256') != NEW
            or review.get('source_sha256') != REVIEW_SOURCE
            or review.get('independent_noop_control_sha256') != NOOP
            or review.get('inputs_unchanged') is not True
            or review.get('raw_original_and_candidate_descriptor_identity') is not False
            or review.get('CAD_or_mesh_modified_by_audit') is not False
            or review.get('manufacturing_authorized') is not False
            or review.get('CFD_qualified') is not False
            or review.get('native_BOP') != CLEAN_BOP):
        raise ValueError('exact_serialization_control_native_merge_review_required')
    if (set(review.get('gates', {})) != set(REVIEW_GATES)
            or any(review['gates'][key] is not True for key in REVIEW_GATES)
            or review.get('topology_before') != {'faces': 88, 'edges': 195, 'vertices': 120, 'solids': 1, 'shells': 1}
            or review.get('topology_after') != {'faces': 86, 'edges': 191, 'vertices': 118, 'solids': 1, 'shells': 1}
            or review.get('candidate_merged_face_ids_private') != [37]
            or review.get('external_rim_edge_count') != 16
            or review.get('unmatched_old_face_ids') != []
            or review.get('ambiguous_old_face_ids') != []):
        raise ValueError('complete_exact_merge_review_gates_required')
    expected = {str(i): i if i < 37 else i - 1 if i == 39 else i - 2
                for i in range(1, 89) if i not in GROUP}
    mapping = review.get('unchanged_face_map_private', {})
    if mapping != expected or any(type(v) is not int for v in mapping.values()):
        raise ValueError('exact_85_face_correspondence_required')
    relation = {int(i): j for i, j in mapping.items()}
    relation.update({i: 37 for i in GROUP})
    return relation


def transfer_rows(original, review):
    relation = reviewed_face_relation(review)
    native_gates = ('single_solid', 'brep_valid', 'native_roundtrip_valid', 'bop_no_faults',
                    'boundary_assignment_complete', 'positive_intake_curtain', 'guide_extensions_communicate')
    if (original.get('schema') != 'm64-intake-gas-domain/v1'
            or original.get('exports', {}).get('domain_brep', {}).get('sha256') != OLD
            or original.get('inputs_unchanged') is not True
            or any(original.get('gates', {}).get(k) is not True for k in native_gates)
            or original.get('gates', {}).get('step_roundtrip_valid') is not None
            or original.get('STEP_BOP_qualified') is not False
            or original.get('manufacturing_authorized') is not False
            or original.get('CFD_executed') is not False):
        raise ValueError('native_only_reviewed_source_manifest_required')
    rows = original.get('boundary_faces', [])
    if (len(rows) != 88 or {r.get('id') for r in rows} != set(range(1, 89))
            or any(type(r.get('id')) is not int for r in rows)):
        raise ValueError('all_88_source_faces_required')
    if dict(Counter(r['role'] for r in rows)) != original.get('boundary_role_counts'):
        raise ValueError('source_role_counts_mismatch')
    grouped = defaultdict(list)
    for row in rows:
        role = row.get('role')
        labels = row.get('source_match', [])
        # Source overlap labels can include chamber and seat simultaneously.
        # Preserve the separately reviewed final role instead of relabeling it.
        if (role not in ROLES or not labels or not any(s.get('role') == role for s in labels)
                or any(s.get('role') not in ROLES or not isinstance(s.get('source'), str)
                       or not s['source'] for s in labels)):
            raise ValueError('known_explicit_source_roles_required')
        grouped[relation[row['id']]].append(row)
    merge = grouped[37]
    if ({r['id'] for r in merge} != GROUP or {r['role'] for r in merge} != {'walls_port'}
            or any(r['source_match'] != [{'source': 'raw_intake_face_8', 'role': 'walls_port'}] for r in merge)):
        raise ValueError('three_merged_faces_must_share_exact_source_and_role')
    if set(grouped) != set(range(1, 87)):
        raise ValueError('all_86_candidate_faces_must_be_assigned')
    return relation, dict(grouped)


def private_member(parent, relative):
    path = parent / relative
    if (Path(relative).is_absolute() or path.is_symlink()
            or parent.resolve() not in path.resolve().parents):
        raise ValueError('source_members_must_stay_in_private_packet')
    return path


def inherited_evidence(original):
    """Keep old numbers nested and explicitly historical; no fresh intersections."""
    fields = ('local_intake_necks', 'guide_extensions', 'fixture_stem_seal_authority',
              'guide_extension_evidence_transfer', 'local_neck_recheck')
    if any(key not in original for key in fields):
        raise ValueError('explicit_source_neck_and_guide_evidence_required')
    return {'original_domain_sha256': OLD, 'original_manifest_sha256': MANIFEST,
            'native_merge_control_review_sha256': REVIEW,
            'basis': 'exact boundary/support correspondence against audited OCCT serialization control',
            'raw_original_descriptor_identity_claimed': False,
            'new_neck_intersection_executed': False, 'new_guide_intersection_executed': False,
            'historical_measurements_not_current_candidate_measurements': True,
            'historical_source_records': {key: original[key] for key in fields},
            'guide_communication_meaning': 'Historical annulus-to-original-intake construction overlap, not a new intersection with this final domain.',
            'physical_leakage_or_seals_qualified': False}


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SHELL
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    started = time.monotonic()
    supplied = {args.domain: NEW, args.original_manifest: MANIFEST, args.review: REVIEW,
                Path(__file__): sha(__file__)}
    if any(p.is_symlink() or sha(p) != h for p, h in supplied.items()):
        raise ValueError('exact_candidate_manifest_and_merge_review_required')
    original = json.loads(args.original_manifest.read_text())
    review = json.loads(args.review.read_text())
    relation, grouped = transfer_rows(original, review)
    inherited = inherited_evidence(original)
    supplied[private_member(args.original_manifest.parent, original['exports']['domain_brep']['file'])] = OLD
    for row in original['boundary_faces']:
        supplied[private_member(args.original_manifest.parent, row['file'])] = row['sha256']
    if any(sha(p) != h for p, h in supplied.items()):
        raise ValueError('original_packet_geometry_changed')
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True, mode=0o700)
    (args.output / 'faces').mkdir(mode=0o700)

    def read(path):
        shape = TopoDS_Shape()
        if not BRepTools.Read_s(shape, str(path), BRep_Builder()):
            raise ValueError('native_read_failed')
        return shape

    def indexed(shape, kind):
        result = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, result)
        return result

    native = args.output / 'domain.brep'
    shutil.copyfile(args.domain, native)
    native.chmod(0o600)
    if sha(native) != NEW:
        raise ValueError('native_domain_copy_must_be_bit_identical')
    shape = read(native)
    faces = indexed(shape, TopAbs_FACE)
    topology = {name: indexed(shape, kind).Extent() for name, kind in (
        ('faces', TopAbs_FACE), ('edges', TopAbs_EDGE), ('vertices', TopAbs_VERTEX),
        ('solids', TopAbs_SOLID), ('shells', TopAbs_SHELL))}
    if topology != {'faces': 86, 'edges': 191, 'vertices': 118, 'solids': 1, 'shells': 1}:
        raise ValueError('exact_unified_native_topology_required')
    valid = BRepCheck_Analyzer(shape, True, False, True).IsValid()
    job = BOPAlgo_ArgumentAnalyzer()
    job.SetShape1(shape)
    for mode in ('SelfInterMode', 'SmallEdgeMode', 'RebuildFaceMode', 'ContinuityMode', 'CurveOnSurfaceMode'):
        setattr(job, mode, True)
    job.Perform()
    bop = {'has_faulty': job.HasFaulty(), 'has_errors': job.HasErrors(),
           'has_warnings': job.HasWarnings(), 'faults': [str(x.GetCheckStatus()).split('.')[-1] for x in job.GetCheckResult()]}
    exported = []
    for i in range(1, 87):
        face = TopoDS.Face_s(faces.FindKey(i))
        prop = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, prop, SkipShared=False, UseTriangulation=False)
        center = prop.CentreOfMass()
        box = Bnd_Box()
        BRepBndLib.AddOptimal_s(face, box, False, False)
        target = args.output / 'faces' / ('face-%04d.brep' % i)
        if not BRepTools.Write_s(face, str(target)):
            raise ValueError('native_face_export_failed')
        target.chmod(0o600)
        reread = read(target)
        row_sources = sorted(grouped[i], key=lambda r: r['id'])
        row = {'id': i, 'role': row_sources[0]['role'], 'file': str(target.relative_to(args.output)),
               'sha256': sha(target), 'area': prop.Mass(), 'center': [center.X(), center.Y(), center.Z()],
               'bbox': list(box.Get()), 'surface_type': str(BRepAdaptor_Surface(face, True).GetType()).split('.')[-1],
               'descriptor_method': 'fresh_native_nonadaptive_exact_surfaces_no_triangulation',
               'source_match': [{'source': s['source'], 'role': s['role']} for s in row_sources[0]['source_match']],
               'source_match_inherited_not_new_overlap': True,
               'original_faces': [{'id': r['id'], 'sha256': r['sha256']} for r in row_sources],
               'native_face_reread_valid': indexed(reread, TopAbs_FACE).Extent() == 1 and BRepCheck_Analyzer(reread, True, False, True).IsValid()}
        if not math.isfinite(row['area']) or row['area'] <= 0 or not all(math.isfinite(x) for x in row['center'] + row['bbox']):
            raise ValueError('finite_positive_native_face_descriptors_required')
        exported.append(row)
    vp = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, vp, OnlyClosed=True, SkipShared=False, UseTriangulation=False)
    nonadaptive_volume = vp.Mass()
    vp = GProp_GProps()
    error = BRepGProp.VolumeProperties_s(shape, vp, Eps=1e-9, OnlyClosed=True, SkipShared=False)
    ap = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, ap, SkipShared=False, UseTriangulation=False)
    role_counts = dict(Counter(r['role'] for r in exported))
    expected_roles = dict(original['boundary_role_counts'])
    expected_roles['walls_port'] -= 2
    unchanged = all(sha(p) == h for p, h in supplied.items()) and sha(native) == NEW
    gates = {'single_solid': topology['solids'] == 1, 'brep_valid': valid,
             'native_roundtrip_valid': valid, 'bop_no_faults': bop == CLEAN_BOP,
             'step_roundtrip_valid': None,
             'boundary_assignment_complete': role_counts == expected_roles and len(exported) == 86,
             'positive_intake_curtain': original['gates']['positive_intake_curtain'],
             'guide_extensions_communicate': original['gates']['guide_extensions_communicate'],
             'all_exported_native_faces_reread_valid': all(r['native_face_reread_valid'] for r in exported)}
    accepted = unchanged and all(value is True for name, value in gates.items() if name != 'step_roundtrip_valid')
    report = {'schema': 'm64-intake-gas-domain/v1',
              'status': 'unified_native_packet_ready_for_independent_mesh_attempt_review' if accepted else 'unified_native_packet_rejected',
              'source_sha256': supplied[Path(__file__)], 'OCP_version': OCP.__version__, 'units': original['units'],
              'exports': {'domain_brep': {'file': 'domain.brep', 'sha256': NEW}},
              'topology': topology, 'native_BOP': bop, 'native_roundtrip_BOP': bop, 'gates': gates,
              'STEP_export': None, 'STEP_BOP_qualified': False, 'STEP_status': 'not_executed_on_this_candidate',
              'boundary_role_transfer': {'original_domain_sha256': OLD, 'original_manifest_sha256': MANIFEST,
                  'independent_geometry_review_sha256': REVIEW, 'review_source_sha256': REVIEW_SOURCE,
                  'serialization_control_sha256': NOOP,
                  'basis': 'exact candidate correspondence against reviewed serialization control; raw source descriptor identity is false',
                  'source_match_labels_inherited_not_new_boolean_overlap_measurements': True,
                  'face_index_relation': [[i, relation[i]] for i in sorted(relation)],
                  'relation_is_bijection': False, 'unchanged_one_to_one_faces': 85,
                  'merged_original_faces': sorted(GROUP), 'merged_candidate_face': 37},
              'boundary_faces': exported, 'boundary_role_counts': role_counts,
              'unmatched_faces': [], 'ambiguous_faces': [],
              'gate_evidence_modes': {'positive_intake_curtain': 'inherited_via_reviewed_native_boundary_equivalence',
                  'guide_extensions_communicate': 'inherited_via_reviewed_native_boundary_equivalence'},
              'inherited_geometric_evidence': inherited,
              'receiver': original['receiver'], 'lifts_design_mm': original['lifts_design_mm'],
              'fixture_stem_seal_authority': original['fixture_stem_seal_authority'],
              'new_intersection_executed': False,
              'domain_volume': {'value': vp.Mass(), 'relative_quadrature_estimate_not_bound': error,
                  'requested_eps': 1e-9, 'fresh_measurement_on_candidate': True,
                  'nonadaptive_reference_value': nonadaptive_volume},
              'properties': {'volume': vp.Mass(), 'area': ap.Mass(), 'solids': 1},
              'CFD_executed': False, 'CFD_qualified': False, 'solver_execution_authorized': False,
              'manufacturing_authorized': False, 'M64_fitment_validated': False,
              'independent_closure_audit_accepted': False, 'master_modified': False,
              'inputs_unchanged': unchanged, 'elapsed_seconds': time.monotonic() - started}
    out = args.output / 'gas-domain-report-native-unified.json'
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    out.chmod(0o600)
    print(json.dumps({'packet_prepared': accepted, 'report_sha256': sha(out),
                      'manifest_content_sha256': content_sha(report), 'faces': len(exported),
                      'elapsed_seconds': report['elapsed_seconds']}))
    return 0 if accepted else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('domain', 'original-manifest', 'review', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    raise SystemExit(run(parser.parse_args()))
