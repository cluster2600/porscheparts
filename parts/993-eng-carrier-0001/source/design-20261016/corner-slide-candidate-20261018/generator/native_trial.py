"""One fixed first-window corner slide from rebuilt d64 source; original local gates."""
import ast
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
R = H.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

GATE = load('_existing_local_gates', H / 'local_gates.py')
require, sha, write = GATE.require, GATE.sha, GATE.write
CURRENT = 'd64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624'

def validate_settings(source, baseline):
    require(source['geometry'] == baseline['geometry'] and source['material'] == baseline['material'] and source['load_cases'] == baseline['load_cases'], 'Original source and baseline study differ')
    g = source['geometry']
    require(g['window_scale'] == .9 and g['end_window_scale'] == .4 and g['window_edge_inset_mm'] == 1.5, 'Original window parameters differ')
    require(g['central_back_ribs'] == dict(width_mm=2.8, top_z_mm=30, inboard_y_mm=5), 'The trial dimension must equal the existing rib width')
    require(g['arm_shell'] == dict(depth_mm=44, cap_mm=1.5, web_mm=1.61), 'Original cap and web parameters differ')
    require(source['material']['density_tonne_mm3'] == 4.42e-9 and source['design_constraints']['absolute_mass_ceiling_kg'] == 1.3, 'Original density or mass ceiling differs')
    return g

def authorities(plan):
    validate_settings(json.loads((R / plan['source_settings']).read_text()), json.loads((R / plan['baseline_study']).read_text()))
    expected = json.loads((R / 'expected.json').read_text())
    root = json.loads((R / 'evidence/construction-root.json').read_text())
    body = json.loads((R / 'evidence/body-root.json').read_text())
    require(root['candidate_sha256'] == body['candidate_BREP_sha256'] == expected['candidate_BREP_sha256'] == '24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd', 'Actual geometry provenance differs')
    require(root['measurements'] == expected['actual_measurements'] and body['whole_native_body'] == expected['actual_whole_native_body'], 'Whole retained native measurements differ')
    require(sha(R/'evidence/construction-root.json') == expected['construction_ROOT_sha256'] and root['actual_child_returncode'] == 0 and root['complete_twelve_window_and_four_rail_ledgers'] and root['complete_five_raw_Cuts_and_four_Commons_and_boundary_predicates'], 'Actual construction closure differs')
    return expected

def verify(path, expected, native=False, output=None, runtime_root=None):
    require(sha(path) == expected, 'Plan identity differs')
    p = json.loads(Path(path).read_text())
    require(p['schema'] == 'delivered-corner-slide-source-replay-plan-1' and p['bounds'] == dict(outer=600, inner=560, CPU=[520,540], threads=1, workers=0), 'Original reproduction bounds differ')
    require(p['trial'] == dict(scaled_A_slide_mm=[1.5,15/136],window_index=0,main_scale=.9,X_sides=[-1,1],other_window_branches_unchanged=10,rib_source_unchanged=True,R1_fillet_inherited=False), 'Fixed actual geometry differs')
    manifest = json.loads((R/'manifest.json').read_text())
    names = {str(q.relative_to(R)) for q in R.rglob('*') if q.is_file()}
    require(names == set(manifest['files']) | {'manifest.json'}, 'Complete delivered file set differs')
    before = {name:sha(R/name) for name in manifest['files']}
    require(before == {name:row['sha256'] for name,row in manifest['files'].items()} and all((R/name).stat().st_size == row['bytes'] and not any(q.is_symlink() for q in [R/name,*(R/name).parents]) for name,row in manifest['files'].items()), 'A complete delivered source/input changed')
    before['manifest.json'] = sha(R/'manifest.json')
    runtime = json.loads((R/'dependencies/runtime.json').read_text())
    runtime_root = Path(runtime_root or runtime['runtime_root']).absolute()
    for name,digest in runtime['files_sha256'].items():
        target = runtime_root/name
        require(sha(target) == digest, 'Installed runtime changed: '+name)
        before[str(target)] = digest
    require(sha(Path(sys.executable)) == runtime['files_sha256'][runtime['python_relative']], 'The current interpreter differs from the recorded CAD interpreter')
    p['files_sha256'] = before
    p['native_site'] = str(runtime_root/runtime['native_site_relative'])
    require(before[p['current_BREP']] == CURRENT and before[p['baseline_STEP']] == GATE.BASELINE, 'Reference geometry differs')
    authorities(p)
    require(output is not None, 'Explicit fresh output path required')
    out = Path(output).absolute()
    require(out == out.resolve() and not out.exists() and out.parent.is_dir() and not out.is_relative_to(R) and not any(q.is_symlink() for q in [out,*out.parents]), 'Fresh nonsymlink output outside the bundle with an existing parent required')
    return p,before,out

def strict_empty(summary):
    require(summary['native_topologically_empty'] is True and summary['native_valid'] is True and summary['counts'] == dict(solids=0, faces=0, edges=0, vertices=0) and summary['highest_topological_dimension'] is None, 'Strict containment requires an empty result in every dimension')

def check_branch_ledger(rows, scale):
    require(len(rows) == 6, 'Complete six-row builder window ledger required')
    triangles = [[(78,-25),(146,-20),(80,24)],[(105,24),(217,18),(156,-22)],[(172,-20),(255,-14),(243,15)]]
    for row, (side, index) in zip(rows, [(side,index) for side in (-1,1) for index in range(3)]):
        inset = 2.8 if scale == .9 and index == 0 else 1.5
        require((row['X_side'],row['scale'],row['window_index'],row['inset_mm']) == (side,scale,index,inset), 'A window branch was changed, skipped or reordered')
        points=triangles[index];cx,cy=[sum(p[i]for p in points)/len(points)for i in (0,1)]
        before=[[cx+scale*(x-cx),cy+scale*(y-cy)]for x,y in points]
        applied=index == 0 and scale == .9;slide=[1.5,15/136]if applied else[0.,0.]
        after=[list(p)for p in before];after[0]=[after[0][i]+slide[i]for i in (0,1)]
        require(row['original_scaled_triangle_points_mm']==before and row['scaled_triangle_points_mm']==after and row['scaled_A_slide_mm']==slide and row['corner_slide_applied']is applied, 'Exact source corner slide/unchanged branches differ')
        require(row['rounded_radius_before_offset_mm']==[6,7,5][index]*scale and row['nominal_radius_after_offset_mm']==[6,7,5][index]*scale-inset, 'Original window radius or inset differs')
    return rows

def check_rail_ledger(rows):
    require(len(rows) == 4, 'All four modified outward rails required')
    from fractions import Fraction as Q
    positive = [[Q(22),Q(87,5)],[Q(49,2),Q(87,5)],[Q(132,5),Q(76,5)],[Q(561,20),Q(1043,50)],[Q(149,5),Q(43,5)],[Q(32),Q(32,5)],[Q(35),Q(32,5)]]
    for row,(side,xside) in zip(rows,[(side,xside) for side in (-1,1) for xside in (-1,1)]):
        points = positive if xside > 0 else [[-x,y] for x,y in reversed(positive)]
        expected = [[str(x),str(side*y)] for x,y in points]
        require(row['X_side'] == xside and row['Y_side'] == side and row['control_points_Q'] == expected and row['actual_float_control_points_mm'] == [[float(x),float(side*y)] for x,y in points], 'Actual four-rail source ledger differs')
        require(row['role'] == 'outward_Y_rail' and row['degree'] == 6 and row['amplitude_mm'] == 2.8 and row['law'] == '64*t^3*(1-t)^3' and row['source_cubic_inner_y_mm'] == 5 and row['source_inner_rail_unchanged'] and row['C2_delta_zero_at_both_endpoints'], 'A rail law or original inner rail differs')
    return rows

def run(path, expected, output=None, runtime_root=None):
    began = time.monotonic()
    p, before, out = verify(path, expected, True, output, runtime_root)
    out.mkdir()
    report = dict(schema='single-first-window-corner-slide-1', status='refused_or_incomplete', candidate_qualified=False,
        method='direct_d64_source_rebuild_with_two_first_window_corner_slides_original_ribs_and_local_gates', trial=p['trial'],
        sources_before=before, downstream_checks={key: 'PENDING' for key in GATE.PENDING}, FEA_executed=False,
        old_complete7_law_proof_not_inherited=True, current07b_subset_required=False, post_union_fillet=False, master_replaced=False,
        candidate_version='first-window-root-corner-slide-v1', R1_fillet_inherited=False, full_protected_check_executed=False, copied_study_and_construction_plan_scope='Nominal settings snapshots remain unchanged; effective-trial.json plus all12 before/after window rows declare exactly two corner slides; all four degree6 rib rows are retained.')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('560s fixed first-window corner-slide trial bound')))
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
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape, TopTools_ListOfShape
        from OCP.TopoDS import TopoDS
        OSD_ThreadPool.DefaultPool_s().Init(1)
        volume = load('_unchanged_adaptive_volume', R / p['volume_source'])
        builder = load('_private_first_window_stock', H / 'build_stock.py')
        require(Path(builder.corrected_cad.__file__).resolve() == (R / p['correction_source']).resolve(), 'The private actual correction source differs')
        require(builder.SOURCE == R/'payload/parts/993-eng-carrier-0001/source/design-20261016' and builder.corrected_cad.ROOT == R/'payload', 'Construction source resolved outside the supplied payload')
        write(out / 'effective-trial.json', dict(schema='first-window-corner-slide-effective-override-1', trial=p['trial'], source_changes_sha256=before[str((H / 'source-changes.json').relative_to(R))], nominal_source_settings_sha256=before[p['source_settings']], current_BREP_sha256=CURRENT, copied_builder_study_and_construction_plan_are_historical_nominal_snapshots=True))
        event('before_original_stock_construction', method=report['method'])
        stock_report = builder.build(out / 'regenerated-stock')
        event('after_original_stock_construction', original_builder_report=stock_report)
        report['actual_window_branch_ledgers'] = {}
        for role, scale in (('base-without-ribs', .9), ('outer-window-stock', .4)):
            ledger_path = out / 'regenerated-stock-without-sleeves' / role / 'window-branch-ledger.jsonl'
            rows = check_branch_ledger([json.loads(line) for line in ledger_path.read_text().splitlines()], scale)
            report['actual_window_branch_ledgers'][role] = dict(path=str(ledger_path.relative_to(out)), sha256=sha(ledger_path), rows=rows)
        event('all12_window_branches_verified_exactly_two_corner_slides_ten_unchanged')
        rail_ledger = out / 'regenerated-stock-without-sleeves/rib-width-branch-ledger.jsonl'
        rail_rows = [json.loads(line) for line in rail_ledger.read_text().splitlines()]
        check_rail_ledger(rail_rows)
        report['actual_retained_rail_branch_ledger'] = dict(path=str(rail_ledger.relative_to(out)),sha256=sha(rail_ledger),rows=rail_rows)
        candidate = import_brep(out / 'regenerated-stock/native-body.brep')
        event('rebuilt_candidate_imported_without_union_or_postfillet')
        raw = out / 'candidate-native.brep'
        export_brep(candidate, raw)
        report['outputs_sha256'] = {'candidate-native.brep': sha(raw)}
        event('raw_candidate_saved_before_validity_and_all_local_gates', sha256=sha(raw))
        report['candidate_native_valid'] = candidate.is_valid
        report['candidate_native_solid_count'] = len(candidate.solids())
        summary = GATE.retain_cut_helpers(R / p['strict_cut_source'], dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape, TopExp=TopExp, Bnd_Box=Bnd_Box, BRepBndLib=BRepBndLib, TopAbs_SOLID=TopAbs_SOLID, TopAbs_FACE=TopAbs_FACE, TopAbs_EDGE=TopAbs_EDGE, TopAbs_VERTEX=TopAbs_VERTEX, BRepCheck_Analyzer=BRepCheck_Analyzer, volume=volume, SimpleNamespace=SimpleNamespace, TopoDS=TopoDS, BRep_Tool=BRep_Tool, GProp_GProps=GProp_GProps, BRepGProp=BRepGProp, BRepAdaptor_Surface=BRepAdaptor_Surface))
        summaries = {}
        for name, argument, tool in (('baseline-minus-candidate', None, candidate), ('d64-minus-candidate', None, candidate), ('candidate-minus-d64', candidate, None), ('R1-minus-candidate', None, candidate), ('candidate-minus-R1', candidate, None)):
            reference_source = p['baseline_STEP'] if name == 'baseline-minus-candidate' else p['R1_BREP'] if 'R1' in name else p['current_BREP']
            if name == 'baseline-minus-candidate':
                original = import_step(R / reference_source)
                argument = original
            elif name in ['d64-minus-candidate','R1-minus-candidate']:
                original = import_brep(R / reference_source)
                argument = original
            else:
                original = import_brep(R / reference_source)
                tool = original
            require(original.is_valid and len(original.solids()) == 1, 'Each fresh original reference must be one valid Solid')
            event('fresh_original_import_for_' + name, source=reference_source, independent_of_construction_union_operand=True)
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
        namespace = dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape,TopExp=TopExp,Bnd_Box=Bnd_Box,BRepBndLib=BRepBndLib,TopAbs_SOLID=TopAbs_SOLID,TopAbs_FACE=TopAbs_FACE,TopAbs_EDGE=TopAbs_EDGE,TopAbs_VERTEX=TopAbs_VERTEX,BRepCheck_Analyzer=BRepCheck_Analyzer,TopoDS=TopoDS,BRep_Tool=BRep_Tool,GProp_GProps=GProp_GProps,BRepGProp=BRepGProp,BRepAdaptor_Surface=BRepAdaptor_Surface)
        exec(compile(ast.parse((H/'body_properties.py').read_text()),str(H/'body_properties.py'),'exec'),namespace)
        body = namespace['inspect_native'](candidate.wrapped)
        body['shell_count'] = len(namespace['entities'](candidate.wrapped,TopAbs_SHELL))
        report['fresh_whole_native_body'] = body
        write(out/'fresh-native-body.json',body)
        native_volume, error = volume.precise_volume(candidate)
        current_volume_reference = import_brep(R / p['current_BREP'])
        require(current_volume_reference.is_valid and len(current_volume_reference.solids()) == 1, 'Fresh original stock volume reference must be one valid Solid')
        old_volume, old_error = volume.precise_volume(current_volume_reference)
        report['original_reference_scope'] = 'Fresh original baseline STEP, d64 or R1 BREP import per strict Cut and a separate fresh d64 volume import; no construction operand is reused as reference authority.'
        study = json.loads((R / p['baseline_study']).read_text())
        mass = native_volume * study['material']['density_tonne_mm3'] * 1000
        box = candidate.bounding_box(); bounds = [list(box.min), list(box.max)]
        measurements = dict(native_volume_mm3=native_volume, estimated_relative_integration_error=error, original_stock_volume_mm3=old_volume,
            original_stock_estimated_relative_integration_error=old_error, delta_from_original_stock_volume_mm3=native_volume-old_volume,
            mass_kg=mass, bounds_mm=bounds, candidate_native_valid=report['candidate_native_valid'], candidate_native_solid_count=report['candidate_native_solid_count'])
        write(out / 'local-measurements-before-gates.json', measurements)
        report.update(measurements)
        report['R1_relative_difference_scope'] = dict(R1_minus_candidate=summaries['R1-minus-candidate'], candidate_minus_R1=summaries['candidate-minus-R1'], full_R1_material_retention_required=False, invalid_signed_zero_residue_not_physical_material=True)
        checks = load('_original_four_tool_Common_block', H / 'tool_checks.py')
        contract = json.loads((R / p['interface_contract']).read_text())
        report.update(checks.evaluate(raw, out, contract, json.loads((R / p['source_settings']).read_text()), summary, event, require, write))
        expected = authorities(p)
        comparisons = dict(generated_BREP_bytes_equal=sha(out/'regenerated-stock/native-body.brep') == expected['generated_BREP_sha256'],candidate_BREP_bytes_equal=sha(raw) == expected['candidate_BREP_sha256'],whole_measurements_equal=measurements == expected['actual_measurements'],whole_topology_equal=body == expected['actual_whole_native_body'])
        for role,path in [('base_windows','base-without-ribs/window-branch-ledger.jsonl'),('outer_windows','outer-window-stock/window-branch-ledger.jsonl'),('rails','rib-width-branch-ledger.jsonl')]:
            fresh = [json.loads(line) for line in (out/'regenerated-stock-without-sleeves'/path).read_text().splitlines()]
            retained = [json.loads(line) for line in (R/'expected-ledgers'/(role+'.jsonl')).read_text().splitlines()]
            comparisons[role+'_whole_rows_equal'] = fresh == retained
        helper = sys.modules.get('corrected_cad')
        comparisons['original_volume_helper_origin_equal'] = helper is not None and Path(helper.__file__).resolve() == R/'payload/parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013/corrected_cad.py'
        report['fresh_reproduction_comparisons'] = comparisons
        write(out/'fresh-reproduction-comparisons.json',comparisons)
        require(all(comparisons.values()), 'Fresh reproduction differs; all raw native observations retained; no equivalence fallback')
        require(candidate.is_valid and len(candidate.solids()) == 1, 'One valid candidate Solid required')
        strict_empty(summaries['baseline-minus-candidate'])
        strict_empty(summaries['d64-minus-candidate'])
        added = summaries['candidate-minus-d64']
        require(not added['native_topologically_empty'] and added.get('native_valid') is True and added['material_solid_volume_mm3'] > 0 and all(row['native_valid'] and row['volume_mm3'] > 0 for row in added.get('solids', [])), 'Strict positive valid new addition required')
        require(native_volume > old_volume, 'Adaptive candidate volume must exceed actual d64')
        report.update(GATE.local_gate_flags(summaries['baseline-minus-candidate'], candidate.is_valid, len(candidate.solids()), mass, bounds, p), status='first_window_corner_slide_local_gates_and_four_tools_complete_downstream_PENDING')
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

