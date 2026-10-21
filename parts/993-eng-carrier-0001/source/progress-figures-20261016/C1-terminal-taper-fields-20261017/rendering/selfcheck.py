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
OLD = ROOT / 'work/carrier-process-20261017/bounded-webs-C1-fields-figure-preparation-001'
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
        self.assertEqual(text.encode(), (OLD / 'figure_v2.py').read_bytes())

    def test_five_math_functions_unchanged(self):
        trees = [ast.parse(p.read_text()) for p in [OLD / 'figure_v2.py', HERE / 'figure.py']]
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
        root['native_receipt_sha256'] = '0' * 64
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
        for case, peak_x in [('rigid', -82.1363154569884), ('spring', 82.05343111183448)]:
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
        self.assertIn('post-Build law refusal retained', text)
        self.assertIn('no strength allowable or stress convergence established', text)
        self.assertIn('89 536 C3D10', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
