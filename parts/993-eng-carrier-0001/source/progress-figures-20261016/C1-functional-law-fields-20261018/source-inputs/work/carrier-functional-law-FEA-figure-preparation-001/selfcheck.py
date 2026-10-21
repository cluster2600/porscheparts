"""Small stdlib-only figure contracts and actual closed metadata mutations."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'work/carrier-terminal-taper-FEA-figure-preparation-001'
spec = importlib.util.spec_from_file_location('_new_taper_figure', HERE / 'figure.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Contracts(unittest.TestCase):
    def data(self):
        data = json.loads((HERE / 'data-closed-cases.json').read_text())
        row = data['cases'][0]
        return row['paths'], row['docs'], data['source_files_sha256'], data['root_review']['cases']['rigid']

    def test_complete_inverse(self):
        text = (HERE / 'figure.py').read_text()
        changes = json.loads((HERE / 'source-changes.json').read_text())['substitutions']
        for before, after, *count in reversed(changes):
            self.assertEqual(text.count(after), count[0] if count else 1)
            text = text.replace(after, before)
        self.assertEqual(text.encode(), (OLD / 'figure.py').read_bytes())

    def test_five_math_functions_unchanged(self):
        trees = [ast.parse(p.read_text()) for p in [OLD / 'figure.py', HERE / 'figure.py']]
        functions = [{n.name: ast.dump(n, include_attributes=False) for n in t.body if isinstance(n, ast.FunctionDef)} for t in trees]
        for name in ['maxima_record', 'boundary_values', 'camera_basis', 'project', 'elements']:
            self.assertEqual(functions[0][name], functions[1][name], name)
        m.literal_functions(ROOT, json.loads((HERE / 'pending-plan.json').read_text())['literal_functions'])

    def test_no_scientific_import_at_load(self):
        self.assertFalse(set(sys.modules).intersection({'numpy', 'matplotlib', 'PIL'}))

    def test_actual_whole_case_metadata(self):
        m.validate_case(*self.data())

    def test_cross_case_identity_refuses(self):
        row, docs, hashes, root = self.data()
        docs = copy.deepcopy(docs)
        docs['record']['name'] = 'combined-spring-1000-static'
        with self.assertRaises(ValueError):
            m.validate_case(row, docs, hashes, root)

    def test_field_hash_refuses(self):
        row, docs, hashes, root = self.data()
        hashes[row['field']] = '0' * 64
        with self.assertRaises(ValueError):
            m.validate_case(row, docs, hashes, root)

    def test_ROOT_cross_binding_refuses(self):
        row, docs, hashes, root = self.data()
        root['native_VM_MPa'] = 0
        with self.assertRaises(ValueError):
            m.validate_case(row, docs, hashes, root)

    def test_boundary_global_distinct_and_all_ties(self):
        ties = [dict(VM_MPa=200, element_id=2), dict(VM_MPa=200, element_id=3)]
        record = m.maxima_record(200, 80, 3, ties)
        self.assertEqual(record['all_global_IP_ties'], ties)
        self.assertEqual(record['displayed_boundary_element_VM_max_MPa'], 80)

    def test_wrong_or_nonfinite_maximum_refuses(self):
        for args in [(200, 201, 3, [dict(VM_MPa=200)]), (200, 80, 3, [dict(VM_MPa=199)]), (float('nan'), 80, 3, [])]:
            with self.assertRaises(ValueError):
                m.maxima_record(*args)

    def test_pending_refuses_before_arrays(self):
        plan = json.loads((HERE / 'pending-plan.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pending.json'
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'NON-ARMED'):
                m.verify(path, m.sha(path), True)

    def test_equal_width_opposite_sign_display_crops(self):
        plan = json.loads((HERE / 'pending-plan.json').read_text())
        for case, peak_x in [('rigid', -82.13632624982483), ('spring', 82.05313499495877)]:
            box = plan['display_zoom_XY_mm'][case]
            self.assertEqual(box[1][0] - box[0][0], 50)
            self.assertLess(box[0][0], peak_x)
            self.assertGreater(box[1][0], peak_x)

    def test_no_solver_decimation_or_deformation_exaggeration(self):
        text = (HERE / 'figure.py').read_text()
        self.assertIn('deformation_amplification=1', text)
        self.assertIn("points=xyz if r==0 else xyz+c['u']", text)
        self.assertIn('decimation=False', text)
        names = [ast.unparse(n.func) for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Call)]
        self.assertFalse(set(names).intersection({'solve', 'mesh', 'subprocess.run', 'Popen'}))

    def test_runtime_recaptured_after_exports(self):
        text = (HERE / 'figure.py').read_text()
        self.assertLess(text.index('fig.savefig('), text.index('loaded_after='))
        self.assertIn('runtime_imported_files=sorted(loaded_after)', text)

    def test_English_diagnostic_scope(self):
        text = (HERE / 'figure.py').read_text()
        self.assertIn('Complete seven-edge function', text)
        self.assertIn('Stress convergence has not been established', text)
        self.assertIn('89 485 C3D10', text)
        self.assertNotIn('Unqualified raw taper:', text)


    def test_both_current_cases_and_mechanic_caption_values(self):
        data=json.loads((HERE/'data-closed-cases.json').read_text())
        for item in data['cases']:
            role=item['paths']['role'];m.validate_case(item['paths'],item['docs'],data['source_files_sha256'],data['root_review']['cases'][role])
            energy=item['docs']['energy'];loads=item['docs']['loads']
            self.assertEqual(energy['E_MPa'],107000);self.assertEqual(energy['nu'],.31)
            self.assertEqual(loads['actual_eye_node_counts'],[2274,2274])
            self.assertEqual(item['docs']['peaks']['CAD_source']['sha256'],'07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e')
    def test_original_runtime_and_scoped_resource_command(self):
        p=json.loads((HERE/'pending-plan.json').read_text());l=json.loads((HERE/'pending-launch.json').read_text())
        self.assertEqual(len(p['runtime_sha256']),219);self.assertEqual(p['outer_seconds'],180);self.assertEqual(p['inner_seconds'],150);self.assertEqual(p['CPU_soft_hard_seconds'],[140,141]);self.assertEqual(l['command'][1],'-B');self.assertNotIn('-I',l['command']);self.assertFalse(l['launch_ready'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
