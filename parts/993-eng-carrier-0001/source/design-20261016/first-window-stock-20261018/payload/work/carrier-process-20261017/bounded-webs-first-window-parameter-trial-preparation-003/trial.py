"""Non-armed single first-window parameter trial; original construction and local gates."""
import importlib.util
import json
import math
import os
import resource
import signal
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

H = Path(__file__).resolve().parent
R = H.parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

GATE = load('_existing_local_gates', H.with_name('bounded-webs-C1-endfillet-preparation-002') / 'close_end.py')
require, sha, write = GATE.require, GATE.sha, GATE.write
CURRENT = '07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e'

def validate_settings(source, baseline):
    require(source['geometry'] == baseline['geometry'] and source['material'] == baseline['material'] and source['load_cases'] == baseline['load_cases'], 'Original source and baseline study differ')
    g = source['geometry']
    require(g['window_scale'] == .9 and g['end_window_scale'] == .4 and g['window_edge_inset_mm'] == 1.5, 'Original window parameters differ')
    require(g['central_back_ribs'] == dict(width_mm=2.8, top_z_mm=30, inboard_y_mm=5), 'The trial dimension must equal the existing rib width')
    require(g['arm_shell'] == dict(depth_mm=44, cap_mm=1.5, web_mm=1.61), 'Original cap and web parameters differ')
    require(source['material']['density_tonne_mm3'] == 4.42e-9 and source['design_constraints']['absolute_mass_ceiling_kg'] == 1.3, 'Original density or mass ceiling differs')
    return g

def authorities(plan):
    for key, digest in (
        ('current_geometry_ROOT', '0f21cecaa83a50b33618474dc69e1d80e3759fc39df0a48266fb75ba09ed7037'),
        ('current_native_ROOT', '68c5afa2cb79f88839a4e026bb7523f8e7732ce7ac781395a12a92892bd15cd6'),
        ('current_addition_ROOT', '0fbfbcdd69be85199db6dffd20afe4bceb77b7d1d12724dfaf86051436a3ca69'),
        ('current_FEA_ROOT', '2b8c079b19b1c329ad75cec098dd4c044603701a412691e36cac55e01e94db05')):
        require(plan['files_sha256'][plan[key]] == digest, 'A current authority was crossed: ' + key)
    root = json.loads((R / plan['current_geometry_ROOT']).read_text())
    require(root['schema'] == 'root-current07b-two-peak-native-terminal-review-1' and root['status'] == 'closed_actual_RC0_two_local_current_geometry_observations', 'Closed current local geometry observations required')
    require(root['owner_terminal_sha256'] == plan['files_sha256'][plan['current_geometry_terminal']], 'Current local ROOT/owner crossed')
    terminal = json.loads((R / plan['current_geometry_terminal']).read_text())
    require(terminal['status'] == 'closed_actual_RC0_two_current_peak_native_diagnostics' and set(terminal['cases']) == {'rigid', 'spring'}, 'Both current local diagnostics required')
    for key in ('rigid', 'spring'):
        require(terminal['cases'][key]['actual_returncode'] == 0 and terminal['cases'][key]['owned_group_empty'], 'Current diagnostic was not closed RC0')
    validate_settings(json.loads((R / plan['source_settings']).read_text()), json.loads((R / plan['baseline_study']).read_text()))

def verify(path, expected, native=False):
    require(sha(path) == expected, 'Plan identity differs')
    p = json.loads(Path(path).read_text())
    require(p['schema'] == 'single-first-window-parameter-trial-plan-1' and p['bounds'] == dict(outer=600, inner=560, CPU=[520, 540], threads=1, workers=0), 'Reviewed single-trial resources differ')
    require(p['trial'] == dict(main_scale=.9, first_window_index=0, inset_mm=2.8, unchanged_inset_mm=1.5, unchanged_outer_window_scale=.4, both_X_mirrors=True), 'Only the stated first-window trial is allowed')
    if native:
        require(p['launch_ready'] is True and p['root_GO_sha256'] is not None and sha(R / p['root_GO']) == p['root_GO_sha256'], 'NON-ARMED: ROOT review and GO required')
    before = {name: sha(R / name) for name in p['files_sha256']}
    require(before == p['files_sha256'], 'Pinned source/input/runtime differs')
    require(before[p['current_BREP']] == CURRENT and before[p['baseline_STEP']] == GATE.BASELINE, 'Current or original baseline geometry differs')
    authorities(p)
    out = R / p['output_directory']
    require(not out.exists() and not any(q.is_symlink() for q in [out, *out.parents]), 'Fresh nonsymlink output required')
    if not native:
        require(not (R / p['execution_directory']).exists(), 'Fresh supervision required at preflight')
    return p, before, out

def strict_empty(summary):
    require(summary['native_topologically_empty'] is True and summary['native_valid'] is True and summary['counts'] == dict(solids=0, faces=0, edges=0, vertices=0) and summary['highest_topological_dimension'] is None, 'Strict containment requires an empty result in every dimension')

def check_branch_ledger(rows, scale):
    require(len(rows) == 6, 'Complete six-row builder window ledger required')
    for row, (side, index) in zip(rows, [(side, index) for side in (-1, 1) for index in range(3)]):
        expected = 2.8 if scale == .9 and index == 0 else 1.5
        require((row['X_side'], row['scale'], row['window_index'], row['inset_mm']) == (side, scale, index, expected), 'A window branch was changed, skipped or reordered')
        require(row['rounded_radius_before_offset_mm'] == [6, 7, 5][index] * scale and row['nominal_radius_after_offset_mm'] == [6, 7, 5][index] * scale - expected, 'Window radius tradeoff differs')
    return rows

def run(path, expected):
    began = time.monotonic()
    p, before, out = verify(path, expected, True)
    out.mkdir()
    report = dict(schema='single-first-window-parameter-trial-1', status='refused_or_incomplete', candidate_qualified=False,
        method='original_builder_main_first_window_inset2p8_then_union_current07b_and_original_local_gates', trial=p['trial'],
        sources_before=before, downstream_checks={key: 'PENDING' for key in GATE.PENDING}, FEA_executed=False,
        old_complete7_law_proof_not_transferred_to_union=True, master_replaced=False,
        copied_study_and_construction_plan_scope='Historical nominal source snapshots; effective-trial.json and the actual per-window ledgers declare the first-window override.')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('560s first-window trial bound')))
    signal.alarm(560)
    resource.setrlimit(resource.RLIMIT_CPU, (520, 540))
    events = (out / 'events.jsonl').open('x')
    def event(name, **values):
        events.write(json.dumps(dict(event=name, seconds=time.monotonic()-began, **values), allow_nan=False) + '\n')
        events.flush(); os.fsync(events.fileno())
    code = 1
    try:
        require(os.getpriority(os.PRIO_PROCESS, 0) == 10, 'nice10 child required')
        sys.path.insert(0, str(R / p['native_site']))
        from build123d import import_step, import_brep, export_brep
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.BRepTools import BRepTools
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_ListOfShape
        from OCP.TopoDS import TopoDS
        OSD_ThreadPool.DefaultPool_s().Init(1)
        volume = load('_unchanged_adaptive_volume', R / p['volume_source'])
        builder = load('_private_first_window_stock', H / 'build_stock.py')
        require(Path(builder.corrected_cad.__file__).resolve() == (R / p['volume_source']).resolve(), 'The retained correction builder import differs')
        write(out / 'effective-trial.json', dict(schema='first-window-effective-override-1', trial=p['trial'], source_changes_sha256=before[str((H / 'source-changes.json').relative_to(R))], nominal_source_settings_sha256=before[p['source_settings']], current_BREP_sha256=CURRENT, copied_builder_study_and_construction_plan_are_historical_nominal_snapshots=True))
        event('before_original_stock_construction', method=report['method'])
        stock_report = builder.build(out / 'regenerated-stock')
        event('after_original_stock_construction', original_builder_report=stock_report)
        report['actual_window_branch_ledgers'] = {}
        for role, scale in (('base-without-ribs', .9), ('outer-window-stock', .4)):
            ledger_path = out / 'regenerated-stock-without-sleeves' / role / 'window-branch-ledger.jsonl'
            rows = check_branch_ledger([json.loads(line) for line in ledger_path.read_text().splitlines()], scale)
            report['actual_window_branch_ledgers'][role] = dict(path=str(ledger_path.relative_to(out)), sha256=sha(ledger_path), rows=rows)
        event('all12_window_branches_verified_only_two_targeted')
        stock = import_brep(out / 'regenerated-stock/native-body.brep')
        old = import_brep(R / p['current_BREP'])
        require(all(body.is_valid and len(body.solids()) == 1 for body in (stock, old)), 'Each operand must be one valid Solid')
        event('before_one_union_with_current07b')
        candidate = old + stock
        event('after_one_union_with_current07b')
        raw = out / 'candidate-native.brep'
        export_brep(candidate, raw)
        report['outputs_sha256'] = {'candidate-native.brep': sha(raw)}
        event('raw_candidate_saved_before_validity_and_all_local_gates', sha256=sha(raw))
        report['candidate_native_valid'] = candidate.is_valid
        report['candidate_native_solid_count'] = len(candidate.solids())
        summary = GATE.retain_cut_helpers(R / p['strict_cut_source'], dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape, TopExp=TopExp, Bnd_Box=Bnd_Box, BRepBndLib=BRepBndLib, TopAbs_SOLID=TopAbs_SOLID, TopAbs_FACE=TopAbs_FACE, TopAbs_EDGE=TopAbs_EDGE, TopAbs_VERTEX=TopAbs_VERTEX, BRepCheck_Analyzer=BRepCheck_Analyzer, volume=volume, SimpleNamespace=SimpleNamespace, TopoDS=TopoDS, BRep_Tool=BRep_Tool, GProp_GProps=GProp_GProps, BRepGProp=BRepGProp, BRepAdaptor_Surface=BRepAdaptor_Surface))
        summaries = {}
        for name, argument, tool in (('baseline-minus-candidate', None, candidate), ('current07b-minus-candidate', None, candidate), ('candidate-minus-current07b', candidate, None)):
            if name == 'baseline-minus-candidate':
                original = import_step(R / p['baseline_STEP'])
                argument = original
            elif name == 'current07b-minus-candidate':
                original = import_brep(R / p['current_BREP'])
                argument = original
            else:
                original = import_brep(R / p['current_BREP'])
                tool = original
            require(original.is_valid and len(original.solids()) == 1, 'Each fresh original reference must be one valid Solid')
            event('fresh_original_import_for_' + name, source=p['baseline_STEP'] if name == 'baseline-minus-candidate' else p['current_BREP'], independent_of_construction_union_operand=True)
            cut = BRepAlgoAPI_Cut()
            args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
            args.Append(argument.wrapped); tools.Append(tool.wrapped)
            cut.SetArguments(args); cut.SetTools(tools)
            cut.SetNonDestructive(True); cut.SetRunParallel(False); cut.SetFuzzyValue(0.)
            event('before_' + name, NonDestructive=True, RunParallel=False, FuzzyValue=0.)
            cut.Build(); event('after_' + name, IsDone=cut.IsDone())
            require(cut.IsDone(), 'Native Cut incomplete: ' + name)
            raw_shape = cut.Shape()
            raw_path = out / (name + '-raw.brep')
            if raw_shape.IsNull():
                preservation = dict(path=None, sha256=None, reason='completed_native_Cut_returned_a_null_shape')
            else:
                require(BRepTools.Write_s(raw_shape, str(raw_path)) is True, 'Native raw Cut export failed: ' + name)
                preservation = dict(path=raw_path.name, sha256=sha(raw_path), reason=None)
            write(out / (name + '-raw-preservation.json'), preservation)
            report.setdefault('raw_Cut_preservation', {})[name] = preservation
            summaries[name] = summary(raw_shape)
            write(out / (name + '.json'), summaries[name])
            report['native_Cut_summaries'] = summaries
        native_volume, error = volume.precise_volume(candidate)
        current_volume_reference = import_brep(R / p['current_BREP'])
        require(current_volume_reference.is_valid and len(current_volume_reference.solids()) == 1, 'Fresh current07b volume reference must be one valid Solid')
        old_volume, old_error = volume.precise_volume(current_volume_reference)
        report['original_reference_scope'] = 'Fresh baseline/current source imports for each strict Cut and a separate fresh current volume import; construction union operands are not original authority.'
        study = json.loads((R / p['baseline_study']).read_text())
        mass = native_volume * study['material']['density_tonne_mm3'] * 1000
        box = candidate.bounding_box(); bounds = [list(box.min), list(box.max)]
        measurements = dict(native_volume_mm3=native_volume, estimated_relative_integration_error=error, current07b_volume_mm3=old_volume,
            current07b_estimated_relative_integration_error=old_error, delta_from_current07b_volume_mm3=native_volume-old_volume,
            mass_kg=mass, bounds_mm=bounds, candidate_native_valid=report['candidate_native_valid'], candidate_native_solid_count=report['candidate_native_solid_count'])
        write(out / 'local-measurements-before-gates.json', measurements)
        report.update(measurements)
        require(candidate.is_valid and len(candidate.solids()) == 1, 'One valid candidate Solid required')
        strict_empty(summaries['baseline-minus-candidate'])
        strict_empty(summaries['current07b-minus-candidate'])
        added = summaries['candidate-minus-current07b']
        require(not added['native_topologically_empty'] and added.get('native_valid') is True and added['material_solid_volume_mm3'] > 0 and all(row['native_valid'] and row['volume_mm3'] > 0 for row in added.get('solids', [])), 'Strict positive valid new addition required')
        require(native_volume > old_volume, 'Adaptive candidate volume must exceed current07b')
        report.update(GATE.local_gate_flags(summaries['baseline-minus-candidate'], candidate.is_valid, len(candidate.solids()), mass, bounds, p), status='single_first_window_trial_local_gates_complete_downstream_PENDING')
        code = 0
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        after = {name: sha(R / name) for name in before}
        report.update(sources_after=after, sources_unchanged=before == after, elapsed_seconds=time.monotonic()-began)
        if before != after:
            report['status'] = 'refused_sources_changed'; code = 1
        report['all_partial_outputs_before_assessment_sha256'] = {str(q.relative_to(out)): sha(q) for q in sorted(out.rglob('*')) if q.is_file() and q.name != 'events.jsonl'}
        write(out / 'assessment.json', report)
        event('assessment_written', sha256=sha(out / 'assessment.json'))
        events.close()
    print(json.dumps(dict(status=report['status'], candidate_qualified=False, assessment_sha256=sha(out / 'assessment.json'))), flush=True)
    return code

if __name__ == '__main__':
    mode, path, expected = sys.argv[1:]
    if mode == 'preflight':
        verify(path, expected); print('SOURCE_ONLY: inputs and pending single-trial controls verified')
    elif mode == 'run':
        raise SystemExit(run(path, expected))
    else:
        raise ValueError('Use preflight or run PLAN SHA')
