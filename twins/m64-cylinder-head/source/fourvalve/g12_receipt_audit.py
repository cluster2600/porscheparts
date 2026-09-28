#!/usr/bin/env python3
"""Audit the incomplete G12 campaign receipts after verified archive collection."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import tarfile

REPO = Path(__file__).resolve().parents[4]
VARIANTS = ('centre_w11_local24_foot24_h40', 'centre_w11_local28_foot30_h50')
SIZES = ('2', '1.5', '1')
SIDES = ('intake', 'exhaust')
DIRECTIONS = ('x', 'minus_z')
BASELINE = REPO/'twins/m64-cylinder-head/evidence/g11-support-stiffness-20260926/baseline-replay-comparison.json'
CAD = REPO/'twins/m64-cylinder-head/evidence/g12-local-buttresses-20260926/cad.json'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError('regular bounded JSON file required')
    return json.loads(path.read_text())


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite numeric observation required')
    return value


def vector(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('three-component displacement required')
    values = [number(x) for x in value]
    if math.hypot(*values) <= 0:
        raise ValueError('nonzero journal displacement required')
    return values


def compare(left, right):
    """Raw vector difference, not the difference of scalar vector norms."""
    vectors = {}
    for side in SIDES:
        a, b = vector(left['journal_vectors_mm'][side]), vector(right['journal_vectors_mm'][side])
        delta = [y-x for x, y in zip(a, b)]
        vectors[side] = dict(left_vector_mm=a, right_vector_mm=b, right_minus_left_mm=delta,
                             left_norm_mm=math.hypot(*a), right_norm_mm=math.hypot(*b),
                             norm_reduction_fraction_from_left=1-math.hypot(*b)/math.hypot(*a),
                             vector_difference_norm_mm=math.dist(a, b),
                             vector_relative_change=math.dist(a, b)/math.hypot(*b),
                             scalar_norm_relative_change=abs(math.hypot(*a)-math.hypot(*b))/math.hypot(*b))
    first, second = number(left['stress_p95_MPa']), number(right['stress_p95_MPa'])
    if first <= 0 or second <= 0:
        raise ValueError('positive p95 stress required')
    vector_change = max(row['vector_relative_change'] for row in vectors.values())
    stress_change = abs(first-second)/second
    return dict(journals=vectors, maximum_vector_relative_change=vector_change,
                vector_stabilized_1pct=vector_change <= .01,
                left_stress_p95_MPa=first, right_stress_p95_MPa=second,
                stress_p95_relative_change=stress_change, stress_stabilized_5pct=stress_change <= .05)


def observations(result):
    cases = result['cases']
    if len(cases) != 2 or {row['direction'] for row in cases} != set(DIRECTIONS):
        raise ValueError('both distinct load directions required')
    rows = {}
    for row in cases:
        mechanics = row['mechanics']
        vectors = {side: vector(mechanics['journal_weighted_displacement_mm'][side]) for side in SIDES}
        rows[row['direction']] = dict(journal_vectors_mm=vectors,
            journal_norms_mm={side: math.hypot(*values) for side, values in vectors.items()},
            maximum_journal_motion_mm=max(math.hypot(*v) for v in vectors.values()),
            stress_p95_MPa=number(mechanics['von_Mises_p95_MPa']),
            numerical_crosscheck_passed=row['numerical_crosscheck_passed'] is True,
            equilibrium_passed=mechanics['equilibrium_passed'] is True,
            relative_residual=number(row['relative_residual']),
            direct_nodal_relative_difference=number(row['fresh_direct']['max_nodal_difference_over_max_reference_U']))
    return rows


def qualified(rows):
    return len(rows) == 2 and all(row['numerical_crosscheck_passed'] and row['equilibrium_passed'] for row in rows.values())


def planned_states(records, data):
    states = {ident: {} for ident in VARIANTS}
    for ident in VARIANTS:
        for index, size in enumerate(SIZES):
            record = records.get((ident, size))
            if record:
                if record['status'] == 'completed':
                    states[ident][size] = dict(status='completed', reason='verified_completed_solver_receipt',
                                               qualified_for_comparison=qualified(data[ident][size]))
                else:
                    states[ident][size] = dict(status='failed', reason='worker_'+record['status'],
                                               returncode=record['returncode'], qualified_for_comparison=False)
            else:
                previous = data[ident].get(SIZES[index-1]) if index else None
                reason = ('prior_mesh_not_completed' if index and previous is None else
                          'prior_mesh_numerical_checks_failed' if index and not qualified(previous) else
                          'deadline_case_reserve_gate')
                states[ident][size] = dict(status='not_run', reason=reason, qualified_for_comparison=False,
                                           reason_origin='inferred_from_verified_summary_and_frozen_controller_order')
    return states


def analyze(collection):
    verified = read(collection/'verified.json')
    archive = collection/'collection.tar.xz'
    if verified.get('collection_verified') is not True or verified.get('producer_exit_code') != 0:
        raise ValueError('successful autonomous archive verification required first')
    if archive.is_symlink() or not archive.is_file() or sha(archive) != verified['archive_sha256']:
        raise ValueError('verified archive fingerprint changed')
    with tarfile.open(archive, 'r|*') as handle:
        member = next(iter(handle))
        if member.name != 'g11-collection/collection-inventory.json' or not member.isfile() or member.size > 2_000_000:
            raise ValueError('expected bounded inventory as first archive member')
        inventory = json.load(handle.extractfile(member))
    members = {row['path']: row for row in inventory['files']}
    if len(members) != len(inventory['files']):
        raise ValueError('duplicate archive inventory paths')

    def snapshot(name):
        path = collection/'snapshots'/name
        if name not in members or members[name]['retained'] is not True or sha(path) != members[name]['sha256']:
            raise ValueError('snapshot differs from verified archive inventory')
        return read(path)

    summaries = sorted(name for name in members if re.fullmatch(r'results/summary-\d{4}\.json', name))
    checkpoints = sorted(name for name in members if re.fullmatch(r'results/checkpoint-\d{4}\.json', name))
    if not summaries or not checkpoints:
        raise ValueError('verified final summary and checkpoint required')
    summary_name = summaries[-1]; summary = snapshot(summary_name)
    if (summary['classification'] != 'G12_generic_cold_isolated_central_support_FEA'
            or summary['complete'] is not False
            or summary['cad_receipt_sha256'] != sha(CAD)
            or summary['campaign_source_sha256'] != sha(REPO/'twins/m64-cylinder-head/source/fourvalve/g12_campaign.py')
            or summary['records'] != snapshot(checkpoints[-1])['records']
            or any(summary.get(key) is not False for key in ('manufacturing_authorized', 'engine_start_authorized', 'assembled_stiffness_qualified'))):
        raise ValueError('expected bound incomplete G12 summary and matching checkpoint')
    for source, expected in summary['reused_source_sha256'].items():
        if Path(source).name != source or sha(REPO/'twins/m64-cylinder-head/source/fourvalve'/source) != expected:
            raise ValueError('summary numerical source changed')
    records = {}
    for record in summary['records']:
        key = record['id'], f'{number(record["size_mm"]):g}'
        if key in records or key[0] not in VARIANTS or key[1] not in SIZES or record['status'] not in ('completed', 'failed', 'timeout'):
            raise ValueError('duplicate or out-of-scope summary record')
        records[key] = record
    baseline = next(row for row in read(BASELINE)['central_screen'] if row['id'] == 'centre_w11')
    prior = {row['direction']: row for row in baseline['directions']}
    cad = read(CAD)
    design = {row['id']: row for row in cad['variants'] if row['cad_accepted'] is True}
    data, provenance = {}, {}
    for ident in VARIANTS:
        data[ident] = {}
        for size in SIZES:
            record = records.get((ident, size))
            if record is None or record['status'] != 'completed':
                continue
            if not re.fullmatch(re.escape(f'{ident}-{size}-attempt')+r'\d+/result\.json', record['path']):
                raise ValueError('completed result path differs from its planned case')
            name = 'results/'+record['path']; result = snapshot(name)
            if record['returncode'] != 0 or record['sha256'] != members[name]['sha256']:
                raise ValueError('summary result fingerprint or exit code changed')
            if (result['id'] != ident or result['mesh']['size_mm'] != float(size)
                    or result['component'] != 'central_diaphragm' or result['complete'] is not True
                    or result['cad_receipt_sha256'] != sha(CAD)
                    or result['step_sha256'] != design[ident]['step_sha256']
                    or result['campaign_source_sha256'] != sha(REPO/'twins/m64-cylinder-head/source/fourvalve/g12_campaign.py')
                    or any(result.get(key) is not False for key in ('manufacturing_authorized', 'engine_start_authorized', 'assembled_stiffness_qualified'))):
                raise ValueError('receipt identity or unqualified scope changed')
            if result['journal_forces_N'] != baseline['journal_forces_N']:
                raise ValueError('force vector magnitudes changed versus G11 baseline')
            for source, expected in result['source_sha256'].items():
                if Path(source).name != source or sha(REPO/'twins/m64-cylinder-head/source/fourvalve'/source) != expected:
                    raise ValueError('reused numerical source changed')
            for declared in [result['hashes']]+[row['hashes'] for row in result['cases']]:
                for artifact, expected in declared.items():
                    target = str(Path(name).parent/artifact)
                    if Path(artifact).name != artifact or target not in members or members[target]['sha256'] != expected:
                        raise ValueError('original solver artifact fingerprint differs from archive inventory')
                    if members[target]['retained'] is not True and artifact not in ('matrix.sti', 'matrix.mas'):
                        raise ValueError('required solver artifact omitted from archive')
            data[ident][size] = observations(result)
            provenance[name] = members[name]['sha256']
    variants = {}
    states = planned_states(records, data)
    for ident in VARIANTS:
        meshes = data[ident]
        refinement = {}
        for a, b in (('2', '1.5'), ('1.5', '1')):
            available = all(size in meshes and qualified(meshes[size]) for size in (a, b))
            refinement[f'{a}_to_{b}_mm'] = dict(evaluated=available,
                reason='both_meshes_qualified' if available else 'missing_or_unqualified_mesh',
                directions={direction: compare(meshes[a][direction], meshes[b][direction]) for direction in DIRECTIONS} if available else {})
        final = refinement['1.5_to_1_mm']
        numerical = len(meshes) == 3 and all(qualified(rows) for rows in meshes.values())
        vectors_pass = all(row['vector_stabilized_1pct'] for row in final['directions'].values()) if final['evaluated'] else None
        p95_pass = all(row['stress_stabilized_5pct'] for row in final['directions'].values()) if final['evaluated'] else None
        maximum = max(row['maximum_journal_motion_mm'] for row in meshes['1'].values()) if '1' in meshes and qualified(meshes['1']) else None
        accepted = numerical and vectors_pass is True and p95_pass is True and maximum is not None and maximum <= .040
        if ident in summary['assessments'] and summary['assessments'][ident]['accepted'] is not accepted:
            raise ValueError('independent verdict differs from campaign assessment')
        variants[ident] = dict(planned_cases=states[ident], observations=meshes, refinement=refinement,
            comparison_to_G11_centre_w11_same_2mm={direction: compare(prior[direction], meshes['2'][direction]) for direction in DIRECTIONS} if '2' in meshes and qualified(meshes['2']) else None,
            volume_mm3=design[ident]['volume_mm3'], added_volume_vs_G11_mm3=design[ident]['volume_mm3']-baseline['volume_mm3'],
            numerical_and_equilibrium_checks_passed=numerical,
            final_mesh_vector_stabilized_1pct=vectors_pass, final_mesh_p95_stabilized_5pct=p95_pass,
            maximum_fine_journal_motion_mm=maximum, working_motion_screen_passed=maximum <= .040 if maximum is not None else None,
            design_margin_0p035_passed=maximum <= .035 if maximum is not None else None,
            accepted_isolated_cold_screen=accepted)
    return dict(classification='G12_independent_receipt_arithmetic_after_verified_collection',
                campaign_complete=False, planned_case_count=6, completed_receipt_count=len(provenance),
                summary_sha256=members[summary_name]['sha256'], summary_records=summary['records'],
                independently_resolved_physics=False, manufacturing_authorized=False,
                engine_start_authorized=False, assembled_stiffness_qualified=False,
                archive_sha256=verified['archive_sha256'], instance_id=verified['instance_id'],
                source_sha256=sha(Path(__file__)), baseline_summary_sha256=sha(BASELINE),
                cad_receipt_sha256=sha(CAD), campaign_source_sha256=sha(REPO/'twins/m64-cylinder-head/source/fourvalve/g12_campaign.py'),
                unchanged_journal_forces_N=baseline['journal_forces_N'],
                original_result_and_case_artifact_hashes_match_inventory=True, receipts=provenance,
                limitation='Independent stdlib arithmetic on solver receipts, not a new solve. G11 is retained coarse summary only. Enlarged feet are perfectly fixed in XYZ; gain mixes geometry with idealized support area. Omitted matrices prevent a fresh residual audit from this archive alone.',
                variants=variants)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.collection.resolve(strict=True))
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'analysis_written': str(args.output), 'variants': {
        ident: {key: result[key] for key in ('maximum_fine_journal_motion_mm', 'final_mesh_vector_stabilized_1pct',
             'final_mesh_p95_stabilized_5pct', 'accepted_isolated_cold_screen')} for ident, result in report['variants'].items()}}))
