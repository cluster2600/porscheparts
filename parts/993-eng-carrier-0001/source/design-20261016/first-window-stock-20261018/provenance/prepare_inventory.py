"""Inventory only the explicit closed stock geometry/source delivery; never copy or run CAD."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRIAL = 'work/carrier-process-20261017/bounded-webs-first-window-parameter-trial-preparation-003'
LOCAL = 'work/carrier-process-20261017/bounded-webs-first-window-stock-admission-preparation-001'
CAD = 'work/part-workflow/run-001/cad'
DESIGN = 'parts/993-eng-carrier-0001/source/design-20261016'
BIONIC = 'parts/993-eng-carrier-0001/source/bionic-20261011'
NEW_ROOT_SHA = '49fe101a5813167c156b9ebb506fa789ffc48ddd1190430529cc20554fde112c'
FAILED_ROOT_SHA = '6a9f38c9c4c7bcbb57030fdecf39eea33e2b7d2b88af29e3dabc3f9febdde497'
BREP_SHA = '42da92ccbcf08783e69edba68bbeb56d3963746538d48682a3e495310a88e776'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def path(relative):
    item = PurePosixPath(relative)
    require(item.parts and not item.is_absolute() and item.as_posix() == relative
            and all(p not in ('', '.', '..') for p in item.parts), 'Noncanonical relative path')
    result = ROOT.joinpath(*item.parts)
    for parent in (result, *result.parents):
        require(not parent.is_symlink(), 'Symlink source')
        if parent == ROOT:
            break
    return result


def inspect(relative):
    source = path(relative)
    with source.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and identity(before) == identity(source.lstat()), 'Regular stable FD required')
        digest = hashlib.sha256()
        count = 0
        while block := stream.read(1024 ** 2):
            digest.update(block)
            count += len(block)
        require(identity(before) == identity(os.fstat(stream.fileno())) == identity(source.lstat()), 'Source changed during inventory')
        require(count == before.st_size, 'Short source read')
    return dict(bytes=count, sha256=digest.hexdigest(), observed_identity=identity(before))


def read(relative):
    return json.loads(path(relative).read_bytes())


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    started = time.monotonic()
    rows = {}

    def add(relative, role):
        if relative in rows:
            require(role == rows[relative]['role'], 'Duplicate source role')
            return
        rows[relative] = dict(source=relative, destination='payload/' + relative,
                              role=role, **inspect(relative))

    def names(prefix, values, role):
        for value in values:
            add(prefix + '/' + value, role)

    names(TRIAL, [
        'trial.py', 'build_stock.py', 'normal-builder/cad.py', 'source-changes.json',
        'normal-builder-cad.py.diff', 'bounded-webs-first-window-parameter-trial-preparation-003-build_stock.py.diff',
        'from-001.json', 'trial-from-001.diff', 'from-002.json', 'trial-from-002.diff',
        'boolean-reference-source-note.json', 'selfcheck.py', 'README.md', 'prepare.py',
        'arm.py', 'collect.py', 'ARMING.md', 'pending-plan.json', 'pending-launch-plan.json',
        'pending-command.json', 'plan.json', 'launch-plan.json', 'command.json', 'preflight.json',
        'preparation-assessment.json', 'arming-assessment.json', 'root-source-review-001.json',
        'root-GO-001.json', 'root-terminal-review-001.json', 'terminal-collection.json',
        'actual-tool-terminal.json', 'execution-001/started.json', 'execution-001/execution-receipt.json',
        'execution-001/stdout.log', 'execution-001/stderr.log', 'output-001/assessment.json',
        'output-001/events.jsonl', 'output-001/effective-trial.json',
        'output-001/local-measurements-before-gates.json', 'output-001/candidate-native.brep',
        'output-001/baseline-minus-candidate.json', 'output-001/baseline-minus-candidate-raw-preservation.json',
        'output-001/current07b-minus-candidate.json', 'output-001/current07b-minus-candidate-raw-preservation.json',
        'output-001/candidate-minus-current07b.json', 'output-001/candidate-minus-current07b-raw-preservation.json',
    ], 'stock_producer_and_preserved_failed_union_history')
    names(TRIAL + '/output-001/regenerated-stock', [
        'native-body.brep', 'carrier.step', 'carrier.stl', 'geometry.json', 'native-construction.json',
        'volume-integration.json', 'study.json', 'construction-plan.json', 'source-snapshot.py',
    ], 'actual_stock_geometry_and_construction')
    for branch in ['base-without-ribs', 'outer-window-stock']:
        names(TRIAL + '/output-001/regenerated-stock-without-sleeves/' + branch,
              ['window-branch-ledger.jsonl', 'geometry.json', 'study.json'], 'effective_window_branch_evidence')
    names(TRIAL + '/output-001/regenerated-stock-without-sleeves',
          ['geometry.json', 'study.json', 'requested-study.json', 'source-snapshot.py', 'volume-integration.json'],
          'intermediate_correction_metadata_only')
    names(LOCAL, [
        'admit.py', 'records.py', 'prepare.py', 'arm.py', 'collect.py', 'selfcheck.py', 'README.md',
        'ARMING.md', 'arming-source-derivation.json', 'collector-helper-derivation.json',
        'pending-plan.json', 'pending-launch-plan.json', 'pending-command.json', 'plan.json',
        'launch-plan.json', 'command.json', 'preflight.json', 'preparation-assessment.json',
        'stock-source-assessment.json', 'arming-assessment.json', 'root-source-review-001.json',
        'root-GO-001.json', 'root-terminal-review-001.json', 'terminal-collection.json', 'actual-tool-terminal.json',
    ], 'actual_stock_local_validation_sources_controls_and_closures')
    owner = read(LOCAL + '/terminal-collection.json')
    for relative in sorted(owner['all_outputs']):
        add(relative, 'all_actual_stock_local_validation_outputs')
        expected = owner['all_outputs'][relative]
        require(rows[relative]['sha256'] == expected['sha256'] and rows[relative]['bytes'] == expected['bytes'], 'Closed output differs')
    names(CAD, ['carrier.step', 'native-body.brep', 'study.json', 'geometry.json', 'native-construction.json',
                'volume-integration.json', 'construction-plan.json', 'source-snapshot.py'],
          'original_baseline_native_source_and_distinct_STEP_reference')
    names(DESIGN, ['build_bounded_webs.py', 'normal-builder/cad.py', 'bounded-webs.json', 'bounded-webs-plan.json'],
          'original_builder_and_nominal_configuration')
    names(BIONIC, ['cad.py', 'study-v5.json', 'correction-20261013/corrected_cad.py',
                   'correction-20261013/interface-study.json'], 'original_correction_and_interface_contract_sources')
    for relative in read(BIONIC + '/correction-20261013/interface-study.json')['sources_sha256']:
        if relative not in rows:
            add(relative, 'original_provisional_interface_contract_input')
    names('work/carrier-process-20261017', [
        'bounded-webs-native-BREP-cut-preparation-001/diagnose.py',
        'bounded-webs-BREP-volume-method-diagnostic-preparation-001/compare.py',
        'source010-exposure-preflight-003/supervise.py',
    ], 'unchanged_executed_native_measurement_and_supervisor_helpers')
    names('work/carrier-process-20261017/bounded-webs-C1-full-contour-native-observer-preparation-001',
          ['patched-output-001/candidate-native.brep', 'root-terminal-review-001.json'],
          'historical_07b_failed_union_operand_only_no_law_or_result_transfer')
    add('LICENSE', 'repository_license')
    add('LICENSES.md', 'repository_license_scope')

    root = read(LOCAL + '/root-terminal-review-001.json')
    require(rows[LOCAL + '/root-terminal-review-001.json']['sha256'] == NEW_ROOT_SHA, 'Current stock ROOT differs')
    require(rows[TRIAL + '/root-terminal-review-001.json']['sha256'] == FAILED_ROOT_SHA, 'Failed union ROOT differs')
    require(root['schema'] == 'root-first-window-stock-native-terminal-review-1'
            and root['status'] == 'closed_actual_RC0_saved_stock_local_geometry_and_same_Solid_volume_only', 'Current stock scope differs')
    require(root['owner_terminal_sha256'] == rows[LOCAL + '/terminal-collection.json']['sha256']
            and root['assessment_sha256'] == owner['assessment_sha256'] == rows[LOCAL + '/output-001/assessment.json']['sha256'], 'Current stock evidence join differs')
    require(owner['actual_child_returncode'] == 0 and owner['direct_child_reaped'] and owner['owned_group_empty'], 'Current stock not closed')
    require(rows[TRIAL + '/output-001/regenerated-stock/native-body.brep']['sha256'] == BREP_SHA, 'Wrong candidate')
    require(root['strict_baseline_minus_stock_empty_all_dimensions'] is True
            and root['stock_minus_baseline_positive_valid_solid_count'] == 6
            and root['failed_union_refusal_preserved_and_unused'] is True
            and root['candidate_qualified'] is False and root['new_FEA'] is False, 'Native local scope differs')
    require(root['measurements']['native_FFF_volume_mm3'] == 286840.62122428033
            and root['measurements']['native_adaptive_volume_mm3'] == 286840.58322119113,
            'Use the already observed operator authorities')
    for relative, expected in read(BIONIC + '/correction-20261013/interface-study.json')['sources_sha256'].items():
        require(rows[relative]['sha256'] == expected, 'Original interface source differs')
    local_plan = read(LOCAL + '/plan.json')
    runtime_versions = {}
    for relative, expected in local_plan['files_sha256'].items():
        if relative.endswith('/METADATA') and any(part in relative for part in ('build123d-', 'cadquery_ocp_novtk-', 'numpy-')):
            observed = inspect(relative)
            require(observed['sha256'] == expected, 'Runtime metadata differs')
            fields = dict(line.split(': ', 1) for line in path(relative).read_text().splitlines()
                          if line.startswith(('Name: ', 'Version: ', 'Requires-Python: ')))
            runtime_versions[relative] = dict(fields=fields, sha256=expected, bytes=observed['bytes'], copied=False)

    destinations = [v['destination'] for v in rows.values()]
    require(len(destinations) == len(set(destinations)), 'Destination collision')
    require(all(v['bytes'] < 40 * 1024 ** 2 for v in rows.values()), 'Unexpected large artifact')
    for relative, row in rows.items():
        require(identity(path(relative).lstat()) == row['observed_identity'], 'Source identity changed before sealing')
    inventory = dict(schema='source-only-first-window-stock-geometry-copy-inventory-1',
                     status='SOURCE_ONLY_NO_COPY_PACK_PUBLICATION_OR_NATIVE_RUN',
                     files=rows, file_count=len(rows), total_source_bytes=sum(v['bytes'] for v in rows.values()),
                     all_paths_regular_non_symlink_and_FD_identity_stable=True,
                     all15_local_native_outputs_included=True,
                     failed_union_history_included_but_not_adopted=True,
                     no_runtime_files_copied=True)
    write('source-copy-inventory.json', inventory)
    roles = dict(schema='first-window-stock-delivery-artifact-roles-1', candidate_version='first-window-stock-alone-v1',
                 master=dict(path='payload/' + TRIAL + '/output-001/regenerated-stock/native-body.brep', sha256=BREP_SHA,
                             role='Locally checked stock native BREP; no old07b blend or law inheritance'),
                 stock_STEP=dict(path='payload/' + TRIAL + '/output-001/regenerated-stock/carrier.step',
                                 role='Existing stock-builder STEP with original adaptive readback gate; not the native BREP'),
                 stock_STL=dict(path='payload/' + TRIAL + '/output-001/regenerated-stock/carrier.stl',
                                role='Existing construction STL; no fresh surface, topology or intersection admission'),
                 baseline_STEP=dict(path='payload/' + CAD + '/carrier.step',
                                    role='The de0e55 operand actually used for strict original-baseline retention'),
                 baseline_native_BREP=dict(path='payload/' + CAD + '/native-body.brep',
                                           role='Original pre-STEP baseline source; not substituted for the STEP Cut reference'),
                 failed_union=dict(path='payload/' + TRIAL + '/output-001/candidate-native.brep',
                                   role='Rejected invalid union, preserved as history; never the stock master'),
                 local_ROOT=dict(path='payload/' + LOCAL + '/root-terminal-review-001.json', sha256=NEW_ROOT_SHA),
                 measurements=root['measurements'], all12_actual_ledgers=root['all12_actual_source_window_branch_rows'],
                 already_measured_FFF_is_future_Gmsh_reference=True, volume_observation_to_repeat=False,
                 candidate_qualified=False, fitment_validated=False, manufacturing_authorized=False,
                 downstream=dict(surface_generation_ROOT=None, native_forward_ROOT=None, joint_surface_ROOT=None,
                                 full8_protected_ROOT=None, T10_ROOT=None, rigid_FEA_ROOT=None, spring_FEA_ROOT=None),
                 external_runtime=dict(original_complete_pins_in='payload/' + LOCAL + '/plan.json',
                                       versions_read_without_import=runtime_versions,
                                       binary_runtime_copied=False, native_rebuild_or_portable_replay_executed=False))
    write('artifact-roles.json', roles)
    write('preparation-assessment.json', dict(schema='stock-geometry-inventory-preparation-1',
        status='SOURCE_ONLY_INVENTORY_COMPLETE_NO_COPY', elapsed_seconds=time.monotonic() - started,
        inventory_sha256=inspect(str((HERE / 'source-copy-inventory.json').relative_to(ROOT)))['sha256'],
        roles_sha256=inspect(str((HERE / 'artifact-roles.json').relative_to(ROOT)))['sha256'],
        files=len(rows), bytes=inventory['total_source_bytes'], current_ROOT_sha256=NEW_ROOT_SHA,
        all15_current_outputs_verified_against_owner=True, source_identity_stability_pass=True,
        scientific_imports=False, geometry_parsing=False, raw_files_hashed_as_bytes_only=True,
        native_executed=False, copying_packing_publication_executed=False))
    print(json.dumps(dict(status='SOURCE_ONLY_INVENTORY_COMPLETE_NO_COPY', files=len(rows), bytes=inventory['total_source_bytes'])))


if __name__ == '__main__':
    main()
