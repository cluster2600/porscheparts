"""Package existing prism proofs; the unchanged strict reader decides acceptance.

No native computation is performed. Reference labels in the composed-distance
receipt are retained, while all payloads are copied under relative map paths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from native_prism_case import load_case

READER_SHA256 = 'd4c8131feb365fbbfe8a92a39398bd89d9728916062ed1a2d9c67a19015f9259'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def changed_faces(final_path, repair_path):
    """Return actual final unknown IDs; never index a parent with a sentinel."""
    with np.load(final_path, allow_pickle=False) as final, np.load(repair_path, allow_pickle=False) as patch:
        lookup, mask = final['autorefine_input_face'], patch['repair_changed_face']
        if (lookup.dtype != np.int64 or lookup.shape != (len(final['faces']),) or
                mask.dtype != np.bool_ or mask.shape != (len(patch['faces']),) or
                lookup.min() < 0 or lookup.max() >= len(mask)):
            raise ValueError('Invalid final-to-repair map or explicit changed-face mask')
        return np.flatnonzero(mask[lookup]).tolist()


class Evidence:
    def __init__(self, output, composed):
        self.output, self.composed = output, composed
        self.files, self.identities = {}, {}

    def add(self, path, linked=False):
        path = Path(path).resolve()
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing evidence payload: '+str(path))
        digest = sha(path)
        label = str(path)
        if linked:
            matches = [name for name, value in self.composed['inputs_sha256'].items() if value == digest]
            if label not in matches:
                if len(matches) != 1:
                    raise ValueError('Composed proof does not uniquely bind this payload: '+path.name)
                label = matches[0]
        relative = 'evidence/'+digest+'-'+path.name
        destination = self.output/relative
        if not destination.exists():
            shutil.copy2(path, destination)
        if sha(destination) != digest:
            raise ValueError('Evidence changed while copying')
        previous = self.files.get(label)
        row = dict(path=relative, sha256=digest)
        if previous is not None and previous != row:
            raise ValueError('Conflicting evidence reference label')
        self.files[label], self.identities[path] = row, digest
        return dict(path=label, sha256=digest)

    def verify(self):
        if any(sha(path) != digest for path, digest in self.identities.items()):
            raise ValueError('Original evidence changed while sealing')
        if any(sha(self.output/row['path']) != row['sha256'] for row in self.files.values()):
            raise ValueError('Packaged evidence changed while sealing')


def seal(original_native_job, final_snap_job, distance_job, composed, contacts, pairs,
         frozen_plan, schema, output, *, source_index, repair_candidate_dir=None,
         first_snap_job=None):
    repair = repair_candidate_dir is not None
    if repair != (first_snap_job is not None):
        raise ValueError('Repair candidate and first-snap job must be supplied together')
    if source_index not in (0, 2) or repair != (source_index == 2):
        raise ValueError('This sealer covers the declared central0 and repaired-left2 cases only')
    original, final, distance = map(lambda p: Path(p).resolve(),
                                    (original_native_job, final_snap_job, distance_job))
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Native prism seal output must be new')
    output.parent.mkdir(parents=True, exist_ok=True)
    own, reader_path = sha(__file__), Path(__file__).with_name('native_prism_case.py').resolve()
    reader_sha = sha(reader_path)
    if Path(load_case.__code__.co_filename).resolve() != reader_path or reader_sha != READER_SHA256:
        raise ValueError('The approved strict reader must come from the same source snapshot')
    composition, original_audit, final_audit, contact = map(read,
        (composed, original/'audit.json', final/'audit.json', contacts))
    with tempfile.TemporaryDirectory(prefix='.'+output.name+'-pending-', dir=output.parent) as temporary:
        stage = Path(temporary)
        (stage/'evidence').mkdir()
        evidence = Evidence(stage, composition)
        raw = evidence.add(original/'result.npz', linked=True)
        exact = evidence.add(original/'result.mesh64.exact', linked=True)
        result = evidence.add(final/'result.npz', linked=True)
        schema_ref = evidence.add(schema)
        receipts = {}
        original_prefix, final_prefix = ('original_native', 'final_snap') if repair else ('boolean', 'snap')
        for prefix, job in ((original_prefix, original), (final_prefix, final)):
            for name in ('native', 'audit', 'execution-receipt'):
                receipts[prefix+'_'+name] = evidence.add(job/(name+'.json'),
                    linked=prefix == original_prefix and name in ('native', 'audit'))
        distance_prefix = 'direct_distance' if repair else 'distance'
        for name in ('audit', 'execution-receipt'):
            receipts[distance_prefix+'_'+name] = evidence.add(distance/(name+'.json'), linked=name == 'audit')
        receipts.update(composed_drift=evidence.add(composed), contacts=evidence.add(contacts),
                        pairs=evidence.add(pairs), schema=schema_ref)
        receipts['frozen_repair_plan' if repair else 'frozen_plan'] = evidence.add(frozen_plan)
        with np.load(original/'result.npz', allow_pickle=False) as raw_arrays:
            box_parents = int(np.sum(raw_arrays['all_parent_faces'] >= sum(original_audit['leaf_face_counts'])-12))
        csr = dict(mesh=raw, schema=schema_ref, offsets_key='all_parent_offsets', parents_key='all_parent_faces',
            leaf_role_order=original_audit['leaf_role_order'], leaf_face_counts=original_audit['leaf_face_counts'],
            complete_whole_child_containment=original_audit['native']['source_face_lineage_complete'],
            bbox_parent_matches=box_parents,
            scope='Whole-child exact original parents; encoded final children still require actual contact/exposure proofs. Unknown repaired faces inherit no positive parent.')
        report = dict(schema='prism-envelope-native-audit-v2', source_index=source_index,
            status='accepted_geometric_envelope_with_unclassified_repaired_faces' if repair else 'accepted_geometric_envelope',
            geometry_pass=True, process_anchor_admission=False, final_npz=result, original_raw_npz=raw,
            original_exact_mesh=exact, raw_geometric_parent_CSR=csr,
            final_to_raw_map=dict(mesh=result, key='autorefine_input_face', intermediate=None),
            modified_faces_without_positive_parent_proof=0, receipts=receipts,
            gates=dict(native_exact=original_audit['native_exact_gate_pass'],
                native_final_global_self_intersection_free=final_audit['native']['post_double_self_intersection_free'],
                collinear_faces=final_audit['native']['exact_collinear_output_triangles'],
                strict_topology=final_audit['topology_gate_pass'], composed_finite_drift=composition['pass'],
                raw_igl_pairs=contact['raw_detector_pair_count_unchanged'],
                remaining_nonconforming_pairs=contact['remaining_pair_count']),
            frozen_bound_mm=composition['original_shape_drift_limit_mm'],
            maximum_composed_bound_mm_approx=max(row['composed_upper_bound_mm_approx'] for row in composition['directions'].values()),
            scope='Geometry and the declared finite vertex/barycentre distance samples only. No continuous Hausdorff or process-anchor admission is asserted.')
        if repair:
            repair_dir, first = Path(repair_candidate_dir).resolve(), Path(first_snap_job).resolve()
            patch_ref = evidence.add(repair_dir/'result.npz')
            unknown = changed_faces(final/'result.npz', repair_dir/'result.npz')
            report.update(local_repair_npz=patch_ref, repair_input_snap_npz=evidence.add(first/'result.npz'),
                modified_faces_without_positive_parent_proof=len(unknown), modified_final_face_ids=unknown,
                parent_admission_rule='Changed final faces keep source/source_face=-1 and empty positive CSR. Historical rows never authorize anchors.',
                consolidation_on_accepted_path=False)
            report['final_to_raw_map']['intermediate'] = dict(mesh=patch_ref,
                to_original_raw_key='historical_snap_input_face', changed_mask_key='repair_changed_face',
                positive_parent_offsets_key='all_parent_offsets', positive_parent_faces_key='all_parent_faces',
                historical_offsets_key='historical_parent_offsets', historical_parents_key='historical_parent_faces')
            for name in ('native', 'audit', 'execution-receipt'):
                receipts['repair_input_snap_'+name] = evidence.add(first/(name+'.json'))
            for key, name in (('repair_assessment', 'assessment.json'),
                              ('repair_completion_attestation', 'execution-completion-attestation.json'),
                              ('repair_source', 'repair_ancestral_line_sheet.py')):
                receipts[key] = evidence.add(repair_dir/name)
        audit_path = stage/'native_audit.json'
        audit_path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        mapping = dict(native_audit_sha256=sha(audit_path), all_references_copied=True, files=evidence.files)
        (stage/'local-evidence-map.json').write_text(json.dumps(mapping, indent=2, allow_nan=False)+'\n')
        case = load_case(audit_path)
        case.verify()
        evidence.verify()
        if sha(__file__) != own or sha(reader_path) != reader_sha:
            raise ValueError('Sealer or strict reader changed during packaging')
        assessment = dict(status='passed', native_audit_sha256=sha(audit_path),
            local_evidence_map_sha256=sha(stage/'local-evidence-map.json'),
            source_index=source_index, final_mesh_sha256=result['sha256'],
            unknown_final_faces=int((case.final_to_original_raw_face < 0).sum()),
            payloads=len(evidence.files), all_evidence_map_paths_relative=True,
            strict_reader_verified=True, native_calculation_executed_by_sealer=False,
            sealer_source_sha256=own, strict_reader_source_sha256=reader_sha)
        (stage/'seal-assessment.json').write_text(json.dumps(assessment, indent=2, allow_nan=False)+'\n')
        shutil.copy2(__file__, stage/Path(__file__).name)
        shutil.copy2(reader_path, stage/reader_path.name)
        if output.exists():
            raise ValueError('Native prism seal output appeared during packaging')
        stage.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original-native-job', 'final-snap-job', 'distance-job', 'composed', 'contacts',
                 'pairs', 'frozen-plan', 'schema', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source-index', type=int, required=True)
    parser.add_argument('--repair-candidate-dir', type=Path)
    parser.add_argument('--first-snap-job', type=Path)
    args = vars(parser.parse_args())
    report = seal(**args)
    print(json.dumps(dict(status=report['status'], geometry_pass=report['geometry_pass'],
        process_anchor_admission=report['process_anchor_admission'])))
