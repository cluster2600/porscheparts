"""Read only the closed stock-construction records; no geometry or scientific imports."""
import hashlib
import importlib.util
import json
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
PARENT = H.with_name('bounded-webs-first-window-parameter-trial-preparation-003')
STOCK = PARENT / 'output-001/regenerated-stock'
ROOT_SHA = '6a9f38c9c4c7bcbb57030fdecf39eea33e2b7d2b88af29e3dabc3f9febdde497'
BREP_SHA = '42da92ccbcf08783e69edba68bbeb56d3963746538d48682a3e495310a88e776'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''): digest.update(block)
    return digest.hexdigest()

def read(path): return json.loads(path.read_bytes())
def require(ok, message):
    if not ok: raise ValueError(message)

def closed_stock():
    root_path = PARENT / 'root-terminal-review-001.json'
    require(sha(root_path) == ROOT_SHA, 'Actual closed trial ROOT required')
    root, owner = read(root_path), read(PARENT / 'terminal-collection.json')
    require(root['schema'] == 'root-first-window-trial003-terminal-review-1' and root['status'] == 'closed_actual_RC1_invalid_union_all_measurements_preserved_no_candidate_admission', 'Parent refusal scope differs')
    require(root['owner_terminal_sha256'] == sha(PARENT / 'terminal-collection.json') == 'a12cc97507776881f536bf10064d503c3541b5e2a59b7090112342c98bd20173', 'Actual owner join differs')
    require(owner['actual_child_returncode'] == 1 and owner['direct_child_reaped'] and owner['owned_group_empty'] and owner['fresh_PID_and_PGID_absent'], 'The parent is not closed')
    require(owner['evidence']['failure']['message'] == 'One valid candidate Solid required' and owner['evidence']['complete_measurements_before_gates']['candidate_native_valid'] is False, 'Failed union evidence must remain explicit')
    assessment = read(PARENT / 'output-001/assessment.json')
    require(sha(PARENT / 'output-001/assessment.json') == owner['evidence']['assessment_sha256'], 'Parent assessment crossed')
    require(assessment['sources_before'] == assessment['sources_after'] == read(PARENT / 'plan.json')['files_sha256'] and assessment['sources_unchanged'], 'Parent sources differ')
    geometry, construction, volume, study = [read(STOCK / name) for name in ('geometry.json', 'native-construction.json', 'volume-integration.json', 'study.json')]
    artifacts = {}
    for name in ('native-body.brep', 'carrier.step', 'carrier.stl', 'geometry.json', 'native-construction.json', 'volume-integration.json', 'study.json', 'construction-plan.json', 'source-snapshot.py'):
        path = STOCK / name; row = owner['all_outputs'][str(path.relative_to(R))]
        require(sha(path) == row['sha256'] and path.stat().st_size == row['bytes'], 'A closed stock artifact differs: ' + name)
        artifacts[name] = dict(path=str(path.relative_to(R)), **row)
    require(artifacts['native-body.brep']['sha256'] == BREP_SHA, 'Only the saved stock may become the new candidate')
    require(geometry['generator_sha256'] == artifacts['source-snapshot.py']['sha256'] == sha(PARENT / 'build_stock.py'), 'Executed stock builder differs')
    require(geometry['source_dependencies_sha256'][str(PARENT / 'normal-builder/cad.py')] == sha(PARENT / 'normal-builder/cad.py'), 'Private first-window source differs')
    require(geometry['geometry_sha256'] == {name: artifacts[name]['sha256'] for name in ('carrier.step', 'carrier.stl')}, 'Stock readback identities differ')
    require(construction['native_valid'] is True and construction['native_solid_count'] == 1 and geometry['CAD_valid'] is True and geometry['solid_count'] == 1, 'Saved construction was not one valid Solid')
    require(construction['volume_mm3'] == geometry['volume_mm3'] == volume['adaptive_original_mm3'] and geometry['dense_reference_mass_kg'] == geometry['volume_mm3'] * study['material']['density_tonne_mm3'] * 1000, 'Stock volume/mass records differ')
    require(volume['adaptive_relative_difference'] == volume['adaptive_readback_mm3'] / volume['adaptive_original_mm3'] - 1 and abs(volume['adaptive_relative_difference']) < 1e-8 and geometry['STEP_readback_volume_match'], 'Original stock STEP readback gate differs')
    require(study['geometry'] == read(R / 'work/part-workflow/run-001/cad/study.json')['geometry'], 'Nominal study snapshot differs')
    spec = importlib.util.spec_from_file_location('_closed_window_ledger_only', PARENT / 'trial.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    ledgers = assessment['actual_window_branch_ledgers']
    require(set(ledgers) == {'base-without-ribs', 'outer-window-stock'}, 'Both actual builder ledgers required')
    for role, row in ledgers.items():
        path = PARENT / 'output-001' / row['path']
        require(sha(path) == row['sha256'] and read_lines(path) == row['rows'], 'Actual ledger crossed')
        module.check_branch_ledger(row['rows'], .9 if role == 'base-without-ribs' else .4)
    return dict(candidate_version='first-window-stock-alone-v1', candidate_BREP=artifacts['native-body.brep'],
        source_ROOT_sha256=ROOT_SHA, artifacts=artifacts, original_builder_geometry=geometry, original_native_construction=construction,
        original_STEP_volume_readback=volume, actual_window_branch_ledgers=ledgers,
        copied_study_is_nominal=True, effective_override='Only first mirrored MAIN scale0.9 windows use inset2.8; all ten other branches use1.5.',
        failed_union_preserved=True, failed_union_used_as_candidate=False, current07b_subset_required=False,
        old_complete7_law_inherited=False, fresh_native_validation_and_volume_unobserved=True, candidate_qualified=False)

def read_lines(path): return [json.loads(line) for line in path.read_text().splitlines()]
