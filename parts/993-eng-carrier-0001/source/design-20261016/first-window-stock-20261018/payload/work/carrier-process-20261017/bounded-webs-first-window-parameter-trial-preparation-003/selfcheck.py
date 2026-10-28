"""Small source and refusal checks; no CAD, arrays, mesher or solver imports."""
import ast
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
spec = importlib.util.spec_from_file_location('_trial_stdlib_only', H / 'trial.py')
trial = importlib.util.module_from_spec(spec); spec.loader.exec_module(trial)
changes = json.loads((H / 'source-changes.json').read_text())
settings = json.loads((R / 'parts/993-eng-carrier-0001/source/design-20261016/bounded-webs.json').read_text())
normal = ast.parse((H / 'normal-builder/cad.py').read_text())
assignment = next(n for n in ast.walk(normal) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'inset' for t in n.targets))

def actual_selection(index, scale, geometry=None):
    ns = dict(window_index=index, scale=scale, g=geometry or dict(window_edge_inset_mm=1.5))
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), 'actual_private_normal_builder', 'exec'), ns)
    return ns['inset']

def ledger(scale):
    return [dict(X_side=side, scale=scale, window_index=index, inset_mm=actual_selection(index, scale), rounded_radius_before_offset_mm=[6, 7, 5][index]*scale, nominal_radius_after_offset_mm=[6, 7, 5][index]*scale-actual_selection(index, scale)) for side in (-1, 1) for index in range(3)]

class Checks(unittest.TestCase):
    def test_whole_normal_inverse(self):
        row = changes['sources'][0]; source = (R / row['private']).read_text()
        for change in reversed(row['replacements']):
            self.assertEqual(source.count(change['new']), 1); source = source.replace(change['new'], change['old'], 1)
        self.assertEqual(source.encode(), (R / row['original']).read_bytes())

    def test_whole_bounded_builder_inverse(self):
        row = changes['sources'][1]; source = (R / row['private']).read_text()
        for change in reversed(row['replacements']):
            self.assertEqual(source.count(change['new']), 1); source = source.replace(change['new'], change['old'], 1)
        self.assertEqual(source.encode(), (R / row['original']).read_bytes())

    def test_only_build_function_changes_in_normal(self):
        old = ast.parse((R / changes['sources'][0]['original']).read_text())
        self.assertEqual(ast.dump(next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == 'arm_envelope')), ast.dump(next(n for n in normal.body if isinstance(n, ast.FunctionDef) and n.name == 'arm_envelope')))

    def test_first_main_only(self):
        self.assertEqual([actual_selection(i, .9) for i in range(3)], [2.8, 1.5, 1.5])

    def test_entire_outer_stock_unchanged(self):
        self.assertEqual([actual_selection(i, .4) for i in range(3)], [1.5, 1.5, 1.5])

    def test_actual_selection_needs_no_removed_rib_key(self):
        self.assertEqual(actual_selection(0, .9, {'window_edge_inset_mm': 1.5}), 2.8)

    def test_both_main_mirrors_and_all12_rows(self):
        rows = trial.check_branch_ledger(ledger(.9), .9) + trial.check_branch_ledger(ledger(.4), .4)
        self.assertEqual([(r['X_side'], r['window_index']) for r in rows if r['inset_mm'] == 2.8], [(-1, 0), (1, 0)])
        self.assertEqual(len(rows), 12)

    def test_missing_window_refused(self):
        with self.assertRaises(ValueError): trial.check_branch_ledger(ledger(.9)[:-1], .9)

    def test_wrong_main_window_refused(self):
        rows = ledger(.9); rows[1]['inset_mm'] = 2.8
        with self.assertRaises(ValueError): trial.check_branch_ledger(rows, .9)

    def test_changed_outer_stock_refused(self):
        rows = ledger(.4); rows[0]['inset_mm'] = 2.8
        with self.assertRaises(ValueError): trial.check_branch_ledger(rows, .4)

    def test_reordered_side_refused(self):
        with self.assertRaises(ValueError): trial.check_branch_ledger(list(reversed(ledger(.9))), .9)

    def test_radius_tradeoff_preserved(self):
        self.assertEqual([r['nominal_radius_after_offset_mm'] for r in ledger(.9)[:3]], [6*.9-2.8, 7*.9-1.5, 5*.9-1.5])
        self.assertEqual(ledger(.4)[2]['nominal_radius_after_offset_mm'], .5)

    def test_actual_original_settings(self):
        trial.validate_settings(settings, copy.deepcopy(settings))

    def test_changed_density_refused(self):
        modified = copy.deepcopy(settings); modified['material']['density_tonne_mm3'] *= 2
        with self.assertRaises(ValueError): trial.validate_settings(modified, modified)

    def test_changed_other_window_parameter_refused(self):
        modified = copy.deepcopy(settings); modified['geometry']['end_window_scale'] = .9
        with self.assertRaises(ValueError): trial.validate_settings(modified, modified)

    def test_source_vs_baseline_difference_refused(self):
        modified = copy.deepcopy(settings); modified['geometry']['arm_shell']['cap_mm'] = 2
        with self.assertRaises(ValueError): trial.validate_settings(settings, modified)

    def test_strict_empty_not_volume_only(self):
        empty = dict(native_topologically_empty=True, native_valid=True, counts=dict(solids=0, faces=0, edges=0, vertices=0), highest_topological_dimension=None)
        trial.strict_empty(empty)
        empty['counts']['faces'] = 1
        with self.assertRaises(ValueError): trial.strict_empty(empty)

    def test_raw_saved_before_all_native_cuts(self):
        source = (H / 'trial.py').read_text()
        self.assertLess(source.index('export_brep(candidate, raw)'), source.index("for name, argument, tool in"))
        self.assertLess(source.index("write(out / (name + '.json'), summaries[name])"), source.index("strict_empty(summaries['baseline-minus-candidate'])"))

    def test_existing_gates_remain_original(self):
        self.assertEqual(trial.GATE.local_gate_flags.__code__.co_filename, str(H.with_name('bounded-webs-C1-endfillet-preparation-002') / 'close_end.py'))
        self.assertEqual(trial.GATE.BASELINE, 'de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63')

    def test_entire_trial_literal_inverse_to_001(self):
        record = json.loads((H / 'from-001.json').read_text())
        text = (H / 'trial.py').read_text()
        for change in reversed(json.loads((H / 'from-002.json').read_text())['trial_literal_replacements']):
            self.assertEqual(text.count(change['new']), 1)
            text = text.replace(change['new'], change['old'], 1)
        for change in reversed(record['trial_literal_replacements']):
            self.assertEqual(text.count(change['new']), 1)
            text = text.replace(change['new'], change['old'], 1)
        self.assertEqual(text.encode(), (R / record['trial_original']).read_bytes())

    def test_actual_union_preservation_block_before_invalid_verdict(self):
        tree = ast.parse((H / 'trial.py').read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        body = next(n for n in run.body if isinstance(n, ast.Try)).body
        start = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'raw' for t in n.targets))
        end = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'summary' for t in n.targets))
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            class Candidate:
                @property
                def is_valid(self):
                    self_outer.assertTrue((out / 'candidate-native.brep').is_file())
                    return False
                def solids(self): return []
            self_outer = self
            ns = dict(out=out, candidate=Candidate(), export_brep=lambda body, path: path.write_text('exported-before-verdict'), sha=trial.sha, report={}, event=lambda *a, **k: None)
            exec(compile(ast.Module(body=body[start:end], type_ignores=[]), 'actual_union_preservation_block', 'exec'), ns)
            self.assertFalse(ns['report']['candidate_native_valid'])
            self.assertIn('candidate-native.brep', ns['report']['outputs_sha256'])

    def test_actual_completed_Cut_preservation_block_nonnull_and_null(self):
        tree = ast.parse((H / 'trial.py').read_text())
        loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple) and [getattr(e, 'id', None) for e in n.target.elts] == ['name', 'argument', 'tool'])
        start = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'raw_shape' for t in n.targets))
        end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == 'summaries' for t in n.targets))
        for null in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder)
                class Shape:
                    def IsNull(self): return null
                class Cut:
                    def Shape(self): return Shape()
                class Tools:
                    @staticmethod
                    def Write_s(shape, path): Path(path).write_text('raw-native-double'); return True
                ns = dict(cut=Cut(), out=out, name='retention', BRepTools=Tools, require=trial.require, sha=trial.sha, write=trial.write, report={})
                exec(compile(ast.Module(body=loop.body[start:end], type_ignores=[]), 'actual_Cut_preservation_block', 'exec'), ns)
                row = json.loads((out / 'retention-raw-preservation.json').read_text())
                self.assertEqual((out / 'retention-raw.brep').exists(), not null)
                self.assertEqual(row['reason'] is not None, null)

    def test_all_Cuts_and_measurements_precede_unchanged_gates(self):
        source = (H / 'trial.py').read_text()
        for text in ["strict_empty(summaries['baseline-minus-candidate'])", "strict_empty(summaries['current07b-minus-candidate'])", "'Strict positive valid new addition required'", "'Adaptive candidate volume must exceed current07b'"]:
            self.assertLess(source.index("write(out / 'local-measurements-before-gates.json', measurements)"), source.index(text))
        loop = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple) and [getattr(e, 'id', None) for e in n.target.elts] == ['name', 'argument', 'tool'])
        self.assertNotIn('strict_empty', [n.func.id for n in ast.walk(loop) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)])

    def test_each_actual_Cut_prefix_imports_a_distinct_original(self):
        tree = ast.parse((H / 'trial.py').read_text())
        loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple) and [getattr(e, 'id', None) for e in n.target.elts] == ['name', 'argument', 'tool'])
        end = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'cut' for t in n.targets))
        self.assertNotIn('old', [n.id for n in ast.walk(loop) if isinstance(n, ast.Name)])
        imports = []
        class Body:
            is_valid = True
            def solids(self): return [self]
        def imported(path):
            body = Body(); imports.append((path, body)); return body
        candidate = object()
        for name, argument, tool in [('baseline-minus-candidate', None, candidate), ('current07b-minus-candidate', None, candidate), ('candidate-minus-current07b', candidate, None)]:
            ns = dict(name=name, argument=argument, tool=tool, R=Path('/pinned'), p=dict(baseline_STEP='baseline.step', current_BREP='current.brep'), import_step=imported, import_brep=imported, require=trial.require, event=lambda *a, **k: None)
            exec(compile(ast.Module(body=loop.body[:end], type_ignores=[]), 'actual_fresh_original_Cut_prefix', 'exec'), ns)
            original = ns['tool'] if name == 'candidate-minus-current07b' else ns['argument']
            self.assertIs(original, imports[-1][1]); self.assertIsNot(original, candidate)
        self.assertEqual([str(path) for path, body in imports], ['/pinned/baseline.step', '/pinned/current.brep', '/pinned/current.brep'])
        self.assertEqual(len({id(body) for path, body in imports}), 3)

    def test_actual_volume_uses_another_fresh_original(self):
        tree = ast.parse((H / 'trial.py').read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        body = next(n for n in run.body if isinstance(n, ast.Try)).body
        begin = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'current_volume_reference' for t in n.targets))
        captured = []
        class Body:
            is_valid = True
            def solids(self): return [self]
        fresh = Body()
        class Volume:
            @staticmethod
            def precise_volume(value): captured.append(value); return 1., 0.
        ns = dict(R=Path('/pinned'), p=dict(current_BREP='current.brep'), import_brep=lambda path: fresh, volume=Volume, require=trial.require, old=object())
        exec(compile(ast.Module(body=body[begin:begin+3], type_ignores=[]), 'actual_fresh_current_volume_prefix', 'exec'), ns)
        self.assertEqual(captured, [fresh]); self.assertIsNot(captured[0], ns['old'])

if __name__ == '__main__':
    unittest.main()
