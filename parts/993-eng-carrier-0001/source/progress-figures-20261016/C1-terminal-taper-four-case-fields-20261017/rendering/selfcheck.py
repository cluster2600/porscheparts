"""Small stdlib-only four-case trust joins; no field-array reads or drawing."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'work/carrier-terminal-taper-FEA-figure-preparation-001'
spec=importlib.util.spec_from_file_location('_four_taper_fields',HERE/'figure.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Contracts(unittest.TestCase):
    def data(self,index=0):
        data=json.loads((HERE/'data-closed-cases.json').read_text())
        case=data['cases'][index]
        return case['paths'],case['docs'],data['source_files_sha256'],case['root_case']

    def test_complete_source_inverse(self):
        source=(HERE/'figure.py').read_text()
        for before,after,count in reversed(json.loads((HERE/'source-changes.json').read_text())['substitutions']):
            self.assertEqual(source.count(after),count);source=source.replace(after,before)
        self.assertEqual(source.encode(),(OLD/'figure.py').read_bytes())

    def test_five_math_functions_literal_unchanged(self):
        trees=[ast.parse(p.read_text())for p in [OLD/'figure.py',HERE/'figure.py']]
        functions=[{n.name:ast.dump(n,include_attributes=False)for n in t.body if isinstance(n,ast.FunctionDef)}for t in trees]
        for name in ['maxima_record','boundary_values','camera_basis','project','elements']:
            self.assertEqual(functions[0][name],functions[1][name],name)
        m.literal_functions(ROOT,json.loads((HERE/'pending-plan.json').read_text())['literal_functions'])

    def test_no_scientific_import_at_load(self):
        self.assertFalse(set(sys.modules).intersection({'numpy','matplotlib','PIL'}))

    def test_all_four_actual_whole_case_metadata(self):
        for index in range(4):m.validate_case(*self.data(index))

    def test_cross_case_name_refuses(self):
        row,docs,hashes,root=self.data(1);docs['record']['name']='combined-spring-1000-static'
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_wrong_whole_field_hash_refuses_each_variant(self):
        for index in [0,1]:
            row,docs,hashes,root=self.data(index);hashes[row['field']]='0'*64
            with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_foreign_ROOT_native_receipt_refuses(self):
        for index in [0,1]:
            row,docs,hashes,root=self.data(index);root['native_receipt_sha256']='0'*64
            with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_refined_actual_returncode_refuses(self):
        row,docs,hashes,root=self.data(1);root['actual_tool_returncode']=1
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_refined_whole_output_count_refuses(self):
        row,docs,hashes,root=self.data(1);root['whole_outputs']=30
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_refined_H2_admission_refuses(self):
        row,docs,hashes,root=self.data(1);docs['assessment']['h2_qualified']=True
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_refined_volume_refusal_cannot_be_erased(self):
        row,docs,hashes,root=self.data(1);docs['terminal']['strict_H2_volume_refusal_preserved']=False
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_law_refusal_cannot_be_erased(self):
        row,docs,hashes,root=self.data(1);docs['assessment']['law_original_RC1_preserved']=False
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_candidate_qualification_cannot_be_added(self):
        row,docs,hashes,root=self.data(1);docs['assessment']['candidate_qualified']=True
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_total_K1000_per_eye_axis_not_per_node(self):
        row,docs,hashes,root=self.data(3);docs['loads']['springs'][0]['summed_card_stiffness_N_mm']=1001
        with self.assertRaises(ValueError):m.validate_case(row,docs,hashes,root)

    def test_actual_coarse_refined_load_contracts_identical(self):
        for coarse,fine in [(0,1),(2,3)]:
            a=self.data(coarse);b=self.data(fine)
            self.assertEqual(a[1]['loads'],b[1]['loads'])
            self.assertEqual(a[2][a[0]['loads']],b[2][b[0]['loads']])

    def test_boundary_global_distinct_and_all_ties(self):
        ties=[dict(VM_MPa=200,element_id=2),dict(VM_MPa=200,element_id=3)]
        out=m.maxima_record(200,80,3,ties)
        self.assertEqual(out['all_global_IP_ties'],ties)
        self.assertEqual(out['displayed_boundary_element_VM_max_MPa'],80)

    def test_wrong_or_nonfinite_maximum_refuses(self):
        for args in [(200,201,3,[dict(VM_MPa=200)]),(200,80,3,[dict(VM_MPa=199)]),(float('nan'),80,3,[])]:
            with self.assertRaises(ValueError):m.maxima_record(*args)

    def test_pending_refuses_before_field_reads(self):
        plan=json.loads((HERE/'pending-plan.json').read_text())
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'pending.json';p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'NON-ARMED'):m.verify(p,m.sha(p),True)

    def test_four_cases_and_migrating_display_crops(self):
        p=json.loads((HERE/'pending-plan.json').read_text())
        self.assertEqual([(r['role'],r['mesh_variant'])for r in p['cases']],[('rigid','coarse'),('rigid','raw_refined_diagnostic'),('spring','coarse'),('spring','raw_refined_diagnostic')])
        for index,row in enumerate(p['cases']):
            box=p['display_zoom_XY_mm'][row['case_key']]
            self.assertEqual(box[1][0]-box[0][0],50)
            for peak in self.data(index)[1]['peaks']['all_global_maximum_ties']:
                self.assertLess(box[0][0],peak['reference_undeformed_IP_xyz_mm'][0]);self.assertGreater(box[1][0],peak['reference_undeformed_IP_xyz_mm'][0])
        self.assertLess(self.data(0)[1]['peaks']['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm'][0],0)
        self.assertGreater(self.data(1)[1]['peaks']['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm'][0],0)

    def test_no_solver_decimation_or_deformation_exaggeration(self):
        s=(HERE/'figure.py').read_text();self.assertIn('deformation_amplification=1',s);self.assertIn("points=xyz if r==0 else xyz+c['u']",s);self.assertIn('decimation=False',s)
        calls=[ast.unparse(n.func)for n in ast.walk(ast.parse(s))if isinstance(n,ast.Call)]
        self.assertFalse(set(calls).intersection({'solve','mesh','subprocess.run','Popen'}))

    def test_runtime_recaptured_after_exports(self):
        s=(HERE/'figure.py').read_text();self.assertLess(s.index('fig.savefig('),s.index('loaded_after='));self.assertIn('runtime_imported_files=sorted(loaded_after)',s)

    def test_English_diagnostic_scope_and_four_panels_per_row(self):
        s=(HERE/'figure.py').read_text();self.assertIn('plt.subplots(2,4',s);self.assertIn('refined H2 volume and post-Build law refusals retained',s);self.assertIn('no strength allowable or stress convergence established',s)


if __name__=='__main__':unittest.main(verbosity=2)
