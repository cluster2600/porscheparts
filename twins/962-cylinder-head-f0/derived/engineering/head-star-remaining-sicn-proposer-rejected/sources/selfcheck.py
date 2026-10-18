"""UNRUN stdlib/AST guards for current208 bindings; no NumPy/SciPy/Gmsh imports.

Only actual pure metadata/authority functions are AST-extracted. Reused math has
its original separately recorded guard evidence; these tests do not replay it.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'propose_coordinates.py'
SOURCE_SHA='0edb4c66de7feabd275074544574b48a612e51f70fdd438b0f02934b41fa38cf'


def extracted(name,namespace):
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen current source required')
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(nodes)!=1:raise ValueError('One actual selected metadata function required')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),namespace)
    return namespace[name]


class Guards(unittest.TestCase):
    def proof_fixture(self):
        # Synthetic metadata only. No geometry, runtime or real worker output is fabricated.
        hashes={'a':'1','b':'2','c':'3','d':'4'};classes={'synthetic_class_digest':'5'}
        c=dict(source_mesh_sha256='mesh',source_worker_report_sha256='partial',source_census_sha256='census',source_tagged_array_sha256s=hashes)
        binding=dict(MSH_sha256='mesh',partial_report_sha256='partial',expected_positive_poor_total=208)
        report=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,
            single_partial_replacement_saved_proof=dict(report_sha256='partial',field='after',after_equals_saved_reopen=True,independent_prior_reader_alias_used=False,old210_bins_reused=False),
            direct_fresh_classifications=classes,**hashes)
        peer=dict(decision='CLEAR_COMPLETED_READ_ONLY_CURRENT208_CENSUS_MESH_REMAINS_REJECTED',bindings={'report':{'sha256':'census'}},blockers=[],head_volume_accepted=False)
        proof=dict(array_sha256s=hashes,classifications=classes);calls=[]
        f=extracted('current_census_proof',dict(partial_after_proof=lambda *args:proof,require_after_match=lambda *args:calls.append(args)))
        return f,c,report,binding,peer,proof,calls

    def test_current_partial_proof_joins_and_reused_check_call(self):
        f,c,r,b,p,proof,calls=self.proof_fixture()
        self.assertIs(f(c,r,{}, {}, {},b,p),proof)
        self.assertEqual(calls,[(r,proof,208)])

    def test_stale_proof_mesh_class_and_peer_refuse(self):
        f,c,r,b,p,_,_=self.proof_fixture()
        cases=[]
        q=deepcopy(r);q['single_partial_replacement_saved_proof']['old210_bins_reused']=True;cases.append((c,q,b,p))
        q=deepcopy(r);q['single_optimized_worker_proof']=q.pop('single_partial_replacement_saved_proof');cases.append((c,q,b,p))
        q=deepcopy(c);q['source_mesh_sha256']='old';cases.append((q,r,b,p))
        q=deepcopy(b);q['expected_positive_poor_total']=210;cases.append((c,r,q,p))
        q=deepcopy(r);q['direct_fresh_classifications']={};cases.append((c,q,b,p))
        q=deepcopy(p);q['bindings']['report']['sha256']='old';cases.append((c,r,b,q))
        for args in cases:
            with self.subTest(args=args),self.assertRaises((ValueError,KeyError)):f(args[0],args[1],{}, {}, {},args[2],args[3])

    def test_authority_counts_and_consumed_direct_pins(self):
        held=json.loads((HERE/'held-contract.json').read_text())
        constants={k:held[v] for k,v in [('QUALIFICATION','qualification'),('LIMITS','limits'),('SOLVER','solver'),('GATE','sicn_gate'),('COUNTS','input_counts')]}
        with tempfile.TemporaryDirectory() as raw:
            out=Path(raw)/'head-star-remaining-sicn-proposal-001';out.mkdir();path=out/'frozen-contract.json'
            (out/'run_readback.py').write_text('synthetic controller bytes')
            roles=['source_census','source_census_contract','source_worker_report','source_worker_receipt','source_worker_root_closed','source_census_peer']
            c=dict(schema='962-current-partial-sicn-head-proposer/v1',scope='analytic_current_partial_coordinate_proposal_only',proposal_execution_authorized=True,
                root_and_peer_review_complete=True,selected_runtime_review_complete=True,qualification=held['qualification'],limits=held['limits'],solver=held['solver'],sicn_gate=.1,input_counts=held['input_counts'],output=str(out))
            python=Path(sys.executable).resolve()
            def digest(p):
                p=Path(p)
                return 'a'*64 if p==python else hashlib.sha256(p.read_bytes()).hexdigest()
            c['runtime_files']={str(python):'a'*64};c['input_hashes']={}
            for i,key in enumerate(roles):
                p=out/('synthetic-evidence%d.txt'%i);p.write_text('metadata');c[key]=str(p);c[key+'_sha256']=digest(p);c['input_hashes'][str(p)]=digest(p)
            c['reader_sha256']=digest(SOURCE);c['runner_sha256']=digest(out/'run_readback.py')
            f=extracted('bound_contract',dict(constants,Path=Path,json=json,re=__import__('re'),sys=sys,sha=digest,__file__=str(SOURCE),OUTPUT_NAME=out.name))
            def invoke(value):path.write_text(json.dumps(value));return f(path)
            self.assertEqual(invoke(c),c)
            for key in ['proposal_execution_authorized','root_and_peer_review_complete','selected_runtime_review_complete']:
                bad=deepcopy(c);bad[key]=False
                with self.subTest(key=key),self.assertRaises(ValueError):invoke(bad)
            bad=deepcopy(c);bad['input_counts']['constraints']=5355
            with self.assertRaises(ValueError):invoke(bad)
            bad=deepcopy(c);del bad['input_hashes'][c['source_census_peer']]
            with self.assertRaises(ValueError):invoke(bad)

    def test_exact_reuse_policy_and_finite_diagnostic_precedes_refusal(self):
        held=json.loads((HERE/'held-contract.json').read_text());source=SOURCE.read_text();tree=ast.parse(source)
        funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
        old=Path(held['original_source']);before={n.name:n for n in ast.parse(old.read_text()).body if isinstance(n,ast.FunctionDef)}
        for name in held['source_reuse']['six_math_runtime_helper_AST_names']:
            self.assertEqual(ast.dump(funcs[name],include_attributes=False),ast.dump(before[name],include_attributes=False))
        self.assertEqual(held['solver'],dict(method='SLSQP',maxiter=100,ftol=1e-10,eps=2.**-26))
        self.assertEqual(held['limits'],dict(wall_seconds=300,sampled_RSS_bytes=1024**3,sampled_output_bytes=16*1024**2,threads=2))
        self.assertEqual(held['input_counts'],dict(movable_nodes=155,coordinate_variables=465,variables_with_epigraph=466,constraints=5327,context_nodes=2938))
        self.assertFalse(held['proposal_execution_authorized']);self.assertIsNone(held['actual_child_sha256'])
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='minimize']
        self.assertEqual(len(calls),1);self.assertEqual({k.arg for k in calls[0].keywords},{'method','bounds','constraints','options'})
        diagnostic=[n.lineno for n in ast.walk(funcs['main']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='save' and 'solver-final-state.json' in ast.get_source_segment(source,n)]
        gate=[n.lineno for n in ast.walk(funcs['main']) if isinstance(n,ast.If) and 'not result.success' in ast.get_source_segment(source,n.test)]
        proposal=[n.lineno for n in ast.walk(funcs['main']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='save' and 'coordinate-proposal.json' in ast.get_source_segment(source,n)]
        self.assertTrue(diagnostic and gate and proposal);self.assertLess(max(diagnostic),min(gate));self.assertLess(max(gate),min(proposal))
        self.assertNotIn('import gmsh',source);self.assertIn("is_coordinate_proposal=False",source)


if __name__=='__main__':unittest.main()
