"""Small stdlib checks; no SSH, compiler or native import."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('restored_cgal_owned_caller',HERE/'run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    rows=[]
    for name,mode,v in [('union-prisms','union',4000),('intersection-prisms','intersection',2000),('difference-prism-gap','difference',3200)]:
        rows.append(dict(name=name,mode=mode,actual_worker_returncode=0,actual_native_returncode=0,passed=True,
            actual_exact_volume_mm3=str(v),expected_exact_volume_mm3=str(v),native_exact_gate_pass=True,
            rounded_exact_contact_gate_pass=True,source_face_lineage_complete=True,output_topology={'pass':True}))
    return dict(status='three_existing_binary_witnesses_passed',global_admission=False,cases=rows)

class Checks(unittest.TestCase):
    def test_real_plan_source_and_all_local_pins(self):
        plan=json.loads((HERE/'plan.json').read_text())
        self.assertEqual(plan['caller_sha256'],m.sha(HERE/'run.py'))
        for p,h in plan['files_sha256'].items():self.assertEqual(m.sha(p),h,p)

    def test_four_scopes_and_approved_limits(self):
        p=json.loads((HERE/'plan.json').read_text())
        self.assertEqual([s['id']for s in p['stages']],['restore','configure','compile','smoke'])
        self.assertEqual(len(set(p['payload']['units'])),4)
        self.assertEqual(p['global_seconds'],900);self.assertEqual(p['cleanup_reserve_seconds'],60)
        for s in p['stages']:
            for value in ['CPUQuota=100%','MemoryMax=6G','MemorySwapMax=0','--unshare-net','--ro-bind']:
                self.assertIn(value,s['argv'])
        self.assertIn('--parallel',p['stages'][2]['argv']);self.assertEqual(p['stages'][2]['argv'][-1],'1')

    def test_complete_positive_receipt(self):m.validate_smokes(fixture())

    def test_missing_duplicate_or_wrong_order_refused(self):
        for rows in [fixture()['cases'][:-1],fixture()['cases']+[fixture()['cases'][0]],list(reversed(fixture()['cases']))]:
            d=fixture();d['cases']=rows
            with self.assertRaises(ValueError):m.validate_smokes(d)

    def test_each_existing_gate_and_actual_rc_refused(self):
        for key in ['passed','native_exact_gate_pass','rounded_exact_contact_gate_pass','source_face_lineage_complete']:
            d=fixture();d['cases'][0][key]=False
            with self.assertRaises(ValueError):m.validate_smokes(d)
        for key in ['actual_worker_returncode','actual_native_returncode']:
            d=fixture();d['cases'][1][key]=2
            with self.assertRaises(ValueError):m.validate_smokes(d)

    def test_exact_wrong_volume_and_promotion_refused(self):
        d=fixture();d['cases'][0]['actual_exact_volume_mm3']='4000000000000000000000001/1000000000000000000000'
        with self.assertRaises(ValueError):m.validate_smokes(d)
        d=fixture();d['global_admission']=True
        with self.assertRaises(ValueError):m.validate_smokes(d)

    def query(self,returncode,text):
        code=ast.parse((HERE/'remote_check.py').read_text())
        function=next(n for n in code.body if isinstance(n,ast.FunctionDef)and n.name=='query')
        ns=dict(subprocess=SimpleNamespace(run=lambda *a,**kw:SimpleNamespace(returncode=returncode,stdout=text)))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'retained_scope_query','exec'),ns)
        return ns['query']('only-owned.scope')

    def test_absent_scope_is_explicit(self):
        self.assertTrue(self.query(4,'LoadState=not-found\nActiveState=inactive\nControlGroup=\n')['absent'])

    def test_query_error_is_not_absence(self):
        for rc,text in [(1,''),(255,''),(1,'LoadState=loaded\nActiveState=active\n'),(4,'LoadState=not-found\nActiveState=active\nControlGroup=x\n')]:
            with self.assertRaises(ValueError):self.query(rc,text)

if __name__=='__main__':unittest.main(verbosity=2)
