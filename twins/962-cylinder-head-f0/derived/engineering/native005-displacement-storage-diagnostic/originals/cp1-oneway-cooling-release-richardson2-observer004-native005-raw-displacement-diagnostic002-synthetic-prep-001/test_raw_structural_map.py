"""HELD/UNRUN six analytic structural-map cases; source-only preparation.

A future separately admitted Python3.12.11 -B -I -S call may run this script.
Only the two SHA-verified first-party Python sources are read. No native data,
CDF/PETSc/CSV, SciPy, runtime probes, child process or output file is used.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import traceback
import types

ROOT=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
SOURCES={
    'parser':dict(path='work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-saved-measurement-parser-prep-002/parse_saved_measurement.py',sha256='dfce01d6cd8d7618e0dee794d35a7bb0a56e34ae998facf2dd3f7b9335d4bede',bytes=13042),
    'target':dict(path='work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-raw-displacement-diagnostic-prep-002/diagnose_raw_displacements.py',sha256='57c38236c17d1744c0bb6003621ad99c43e6d4043957bf9e37827621f69a612a',bytes=15171),
}
KNOWN_NAMES=('disp_x','disp_y','disp_z','inactive_placeholder')
VARIABLE_NUMBERS=(2,0,3,1)
OBSERVED_SCALING=(2.0,0.5,4.0,8.0)
CASE_NAMES=('valid_permuted_map','wrong_exact_time','wrong_coordinate',
            'signed_zero_coordinate','duplicate_global_DOF','missing_physical_DOF')


def check(ok,message):
    if not ok:
        raise AssertionError(message)


def read_verified(pin):
    path=ROOT/pin['path']
    check(path.is_file() and not path.is_symlink() and path.resolve(strict=True)==path,
          'Exact canonical regular source required')
    with path.open('rb') as stream:
        raw=stream.read(pin['bytes']+1)
    check(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],
          'Exact source SHA/bytes required before any compilation')
    return path,raw


def load_verified(role):
    path,raw=read_verified(SOURCES[role])
    # Whole verified source, fresh ordinary globals. No importlib/pyc cache and
    # no function extraction, fixture globals, NAMES or helpers injected.
    module=types.ModuleType('_rawdiag002_synthetic_'+role)
    module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    check('NAMES' not in module.__dict__ if role=='target' else module.NAMES==KNOWN_NAMES,
          'Target globals must not inherit fixture NAMES; parser owns its tuple')
    check(read_verified(SOURCES[role])[1]==raw,'Source changed during loading')
    return module


def word(value):
    return struct.pack('<d',value).hex()


def synthetic_map():
    # Synthetic Cartesian triples and tokens are invented analytic inputs;
    # their ID order is not an observation of the native coupon.
    coords=[[word((node//25)/8),word(((node//5)%5)/4),word((node%5)/4)]
            for node in range(425)]
    time_word=word(0.4525)
    rows=[]
    expected=[]
    for node in range(425):
        for slot in range(4):
            present=slot<3
            index=(37*(node*3+slot)+23)%1275 if present else None
            rows.append(dict(source_node_ID=node,variable_slot=slot,
                variable_number=VARIABLE_NUMBERS[slot],
                coordinate_binary64_LE_hex=list(coords[node]),dof_present=present,
                DOF_state='present' if present else 'absent',global_DOF=index,
                constrained=(node==0 and slot<3) or (node==32 and slot in (1,2))
                            or (node==137 and slot==2)))
            if present:
                expected.append(dict(source_node_ID=node,slot=slot,global_DOF=index))
    variables=[dict(slot=s,name=KNOWN_NAMES[s],number=VARIABLE_NUMBERS[s],
                   family='LAGRANGE',order='FIRST',physical_displacement=s<3,
                   existing_scaling_binary64_LE_hex=word(OBSERVED_SCALING[s]))
               for s in range(4)]
    mapping=dict(schema='962-RICH2-END181-node-global-DOF-map/v1',
        scope='integer_associations_only_no_field_acceptance',
        constraint_mask_scope='original_case_expected_labels_not_live_BC_or_DofMap_observation',
        step=181,event='TIMESTEP_END',nonlinear_system_name='nl0',
        nonlinear_system_number=0,physical_displacement_DOF_count=1275,
        source_node_count=425,MPI_ranks=1,threads=1,Real_bytes=8,PetscScalar_bytes=8,
        PetscInt_bytes=4,PETSc_version=[3,25,4],global_DOF_count=1275,
        time_binary64_LE_hex=time_word,dt_binary64_LE_hex=word(0.0025),
        variables=variables,rows=rows,
        reaction_convention=dict(system='auxiliary_save_in',save_in=['rx','ry','rz'],
            DOF_presence_is_not_kernel_activation=True,
            reaction_values_recorded_by_this_observer=False,
            unchanged_END181_collector_required=True,solver_F_has_nodal_BC_rows=True,
            constrained_F_is_not_reaction=True,scaling_changed_or_removed=False),
        assembly_invoked=False,solution_or_physical_state_written=False,
        field_acceptance=False)
    check(len(rows)==1700 and len(expected)==1275 and
          {r['global_DOF'] for r in expected}==set(range(1275)),
          'Analytic input construction must cover the complete permuted range')
    return mapping,coords,time_word,expected


def valid_case(target,parser):
    mapping,coords,time_word,expected=synthetic_map()
    before=json.dumps(mapping,sort_keys=True)
    result=target.structural_map(mapping,coords,time_word,parser)
    check(result['ndof']==1275 and result['integer_bytes']==4,
          'Observed full range and integer width must survive')
    check(result['physical_rows']==expected and len(result['physical_rows'])==1275,
          'Every physical source/component/permuted global index must survive')
    check(result['expected_mask_labels']==[[0,0],[0,1],[0,2],[32,1],[32,2],[137,2]],
          'Only the six original expected labels are represented')
    check(result['observed_dt_binary64_LE_hex']==mapping['dt_binary64_LE_hex'] and
          result['observed_scaling_words']==[word(x) for x in OBSERVED_SCALING],
          'Observed finite dt/scaling must be retained without substitution')
    for key in ('actual_dt_independently_verified','scaling_independently_verified',
                'strict_validate_map_called','strict_semantic_validation_passed',
                'installed_ABI_proved','live_BC_observed',
                'field_or_SI_force_or_reaction_accepted'):
        check(result[key] is False,'No semantic/field/ABI promotion: '+key)
    check(result['transfer_Exodus_coordinate_and_map_Exodus_time_words_compared'] is True
          and result['common_solver_origin_internal_storage_consistency_only'] is True,
          'Only declared synthetic association/common-origin scope is represented')
    check(json.dumps(mapping,sort_keys=True)==before,'Input map must not be rewritten')
    return dict(physical_rows_checked=1275,global_DOF_permutation_complete=True,
                placeholder_rows_absent=425,dt_scaling_independently_verified=False)


def refusal_case(name,target,parser):
    mapping,coords,time_word,_=synthetic_map()
    if name=='wrong_exact_time':
        time_word=word(0.5)
        expected_error='Exact map/Exodus event-time word mismatch'
    elif name=='wrong_coordinate':
        mapping['rows'][4]['coordinate_binary64_LE_hex'][0]=word(99.0)
        expected_error='Node coordinate word mismatch across slots/current capture'
    elif name=='signed_zero_coordinate':
        check(coords[0][0]==word(0.0) and word(-0.0)!=word(0.0),
              'Signed-zero negative input must differ in its raw word')
        mapping['rows'][0]['coordinate_binary64_LE_hex'][0]=word(-0.0)
        expected_error='Node coordinate word mismatch across slots/current capture'
    elif name=='duplicate_global_DOF':
        mapping['rows'][1]['global_DOF']=mapping['rows'][0]['global_DOF']
        expected_error='Duplicate/out-of-range global index'
    elif name=='missing_physical_DOF':
        mapping['rows'][0].update(dof_present=False,DOF_state='absent',global_DOF=None)
        # The earlier absent-placeholder guard refuses this missing physical
        # component; no row is removed to trigger only a length check.
        expected_error='Only placeholder may be absent with null index'
    else:
        raise AssertionError('Unknown fixed analytic case')
    try:
        target.structural_map(mapping,coords,time_word,parser)
    except ValueError as error:
        check(str(error)==expected_error,'Specific actual source refusal required')
        return dict(exception_type='ValueError',message=str(error))
    raise AssertionError('Faulted input was accepted: '+name)


def main():
    check(sys.version_info[:3]==(3,12,11),'Future root-selected Python3.12.11 required')
    check(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
          'Future isolated -B -I -S invocation required')
    parser=load_verified('parser')
    target=load_verified('target')
    check(target.structural_map.__globals__ is target.__dict__ and
          parser.need.__globals__ is parser.__dict__,
          'Actual whole-source functions must use their fresh own module globals')
    results=[]
    for name in CASE_NAMES:
        try:
            detail=valid_case(target,parser) if name==CASE_NAMES[0] else refusal_case(name,target,parser)
            results.append(dict(case=name,status='PASS',detail=detail))
        except Exception as error:
            results.append(dict(case=name,status='FAIL',exception_type=type(error).__name__,
                                message=str(error),traceback=traceback.format_exc()))
    for pin in SOURCES.values():
        read_verified(pin)
    passed=all(row['status']=='PASS' for row in results)
    report=dict(schema='962-native005-rawdiag002-six-case-synthetic-result/v1',
        status='ALL_SIX_ANALYTIC_CASES_PASSED' if passed else 'SYNTHETIC_CASE_FAILURES',
        sources=SOURCES,case_count=len(results),cases=results,
        whole_verified_source_fresh_namespaces=True,cached_pyc_used=False,
        fixture_globals_injected_into_target=False,actual_dt_scaling_semantics_verified=False,
        scientific_file_decoder_or_real_capture_called=False,strict_collector_or_validate_map_called=False,
        field_force_physics_material_manufacturing_qualified=False)
    print(json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
    return 0 if passed else 2


if __name__=='__main__':
    raise SystemExit(main())
