"""Small stdlib-only contract checks; no scientific modules, arrays or rendering."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_C1_figure',HERE/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ROOT=HERE.parents[2]

class Contracts(unittest.TestCase):
    def test_original_functions_literal(self):
        m.literal_functions(ROOT,{'scripts/render_carrier_fields.py':['boundary_values','camera_basis','project'],
            'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py':['elements']})
    def test_no_scientific_import_at_load(self):
        self.assertFalse(any(n in sys.modules for n in ['numpy','matplotlib','PIL']))
    def test_global_and_boundary_are_distinct(self):
        p=[dict(VM_MPa=200,element_id=2,IP_one_based=1)]
        result=m.maxima_record(200,80,3,p)
        self.assertEqual(result['global_IP_VM_MPa'],200);self.assertEqual(result['displayed_boundary_element_VM_max_MPa'],80)
    def test_all_ties_preserved(self):
        p=[dict(VM_MPa=200,element_id=2,IP_one_based=1),dict(VM_MPa=200,element_id=3,IP_one_based=4)]
        self.assertEqual(m.maxima_record(200,80,3,p)['all_global_IP_ties'],p)
    def test_wrong_tie_refused(self):
        with self.assertRaises(ValueError):m.maxima_record(200,80,3,[dict(VM_MPa=199)])
    def test_boundary_over_global_refused(self):
        with self.assertRaises(ValueError):m.maxima_record(200,201,3,[dict(VM_MPa=200)])
    def test_nonfinite_refused(self):
        with self.assertRaises(ValueError):m.maxima_record(float('nan'),80,3,[])
    def test_pending_before_imports(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'pending.json';p.write_text(json.dumps(dict(schema='actual-C1-two-case-fields-plan-1',actual_workers=0,deformation_amplification=1,launch_ready=False)))
            with self.assertRaisesRegex(ValueError,'NON-ARMED'):m.verify(p,m.sha(p),True)
    def test_wrong_plan_hash(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'p';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'Plan hash'):m.verify(p,'0'*64)
    def test_fresh_existing_refused(self):
        with tempfile.TemporaryDirectory()as d:
            with self.assertRaises(ValueError):m.fresh(d)
    def test_fresh_dangling_refused(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'link';p.symlink_to(Path(d)/'absent')
            with self.assertRaises(ValueError):m.fresh(p)
    def test_actual_case_contract_and_wrong_case(self):
        data=json.loads((HERE/'data/closed-cases.json').read_text());row=data['cases'][0];docs=copy.deepcopy(row['docs'])
        m.validate_case(row['paths'],docs,data['source_files_sha256'],data['root_review']['cases']['rigid'])
        docs['record']['name']='combined-spring-1000-static'
        with self.assertRaisesRegex(ValueError,'case identity'):m.validate_case(row['paths'],docs,data['source_files_sha256'],data['root_review']['cases']['rigid'])
    def test_cross_case_output_sha_refused(self):
        data=json.loads((HERE/'data/closed-cases.json').read_text());row=data['cases'][0];hashes=dict(data['source_files_sha256']);hashes[row['paths']['field']]='0'*64
        with self.assertRaisesRegex(ValueError,'output differs'):m.validate_case(row['paths'],row['docs'],hashes,data['root_review']['cases']['rigid'])
    def test_root_cross_binding_refused(self):
        data=json.loads((HERE/'data/closed-cases.json').read_text());row=data['cases'][0];root=copy.deepcopy(data['root_review']['cases']['rigid']);root['terminal_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Root closure'):m.validate_case(row['paths'],row['docs'],data['source_files_sha256'],root)
    def test_no_solver_calls_and_unit_deformation(self):
        tree=ast.parse((HERE/'figure.py').read_text());calls=[n.func.attr for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)]
        self.assertFalse(set(calls)&{'solve','mesh','execute','subprocess','Popen','run'})
        s=(HERE/'figure.py').read_text();self.assertIn("deformation_amplification=1",s);self.assertIn("points=xyz if r==0 else xyz+c['u']",s)
    def test_common_scales_all_facets(self):
        s=(HERE/'figure.py').read_text();self.assertIn("vm_scale=max(c['summary']['global_IP_VM_MPa']for c in cases)",s)
        self.assertIn("u_scale=max(c['summary']['all_nodes_Umax_mm']for c in cases)",s)
        self.assertIn("xy[ids][order]",s);self.assertIn("kind='stable'",s)

if __name__=='__main__':unittest.main(verbosity=2)
