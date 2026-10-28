"""ROOT-ONLY selected NumPy/stdlib AST guards; no SciPy/Gmsh/optimizer/head data."""
import ast
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
import warnings

HERE=Path(__file__).resolve().parent
SOURCE_SHA256='20b76607821b83caf342e9741c80e2e02fa41568fa2d5ca413b1d1ab6caa3325'


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c=json.loads((HERE/'held-contract.json').read_text())
        import numpy as np  # Root may run selected literal arithmetic; not imported by author.
        if np.__version__!='2.2.6' or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve():
            raise ValueError('Exact selected NumPy required')
        if hashlib.sha256(Path(c['numpy_init']).read_bytes()).hexdigest()!=c['runtime_files'][c['numpy_init']]:
            raise ValueError('Selected NumPy source changed')
        raw=(HERE/'sparse_head.py').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('Prepared source changed')
        names={'signed_sicn_vector','tagged_indices','assemble_points','jacobian_entries','objective','objective_gradient',
               'zero_objective_hessian','all_quality_at_gate','quality_target_callback','final_quality_gate',
               'refuse_documented_dense_fallback','solver_metadata','coordinate_rows'}
        body=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
        if {n.name for n in body}!=names:raise ValueError('Exact selected helpers required')
        cls.f={'math':math,'warnings':warnings,'GATE':.1}
        exec(compile(ast.Module(body=body,type_ignores=[]),'actual-selected-pure-helpers','exec'),cls.f)
        cls.np=np;cls.c=c

    def test_literal_signed_quality_and_degenerate_refusal(self):
        p=[[0.,0.,0.],[1.,0.,0.],[.5,math.sqrt(3.)/2.,0.],[.5,math.sqrt(3.)/6.,math.sqrt(2./3.)]]
        q=self.f['signed_sicn_vector'](self.np,[p,[p[1],p[0],p[2],p[3]]])
        self.assertTrue(math.isclose(float(q[0]),1.,rel_tol=1e-11,abs_tol=1e-14))
        self.assertLess(q[1],0)
        for bad in [self.np.zeros((1,4,3)),self.np.full((1,4,3),self.np.nan)]:
            with self.assertRaises(ValueError):self.f['signed_sicn_vector'](self.np,bad)

    def test_exact_shared_corner_sparsity_with_common_t(self):
        rows,cols,shape=self.f['jacobian_entries']([1,3,7,9,15],[[1,3,7,9],[3,7,9,15]],[7,15])
        self.assertEqual(shape,(2,7))
        self.assertEqual([(r,c) for r,c in zip(rows,cols)],[(0,0),(0,1),(0,2),(0,6),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5),(1,6)])
        self.assertEqual(len(set(zip(rows,cols))),11)
        with self.assertRaises(ValueError):self.f['jacobian_entries']([1,3,7,9],[[1,3,7,15]],[7])

    def test_scatter_retains_every_unselected_signed_zero_bit(self):
        p=self.np.array([[-0.,1.,2.],[3.,4.,5.],[6.,7.,8.],[9.,10.,11.]],dtype='f8');p.setflags(write=False)
        x=self.np.array([.2,.3,.4,.5,.6,.7,.08]);after=self.f['assemble_points'](self.np,p,[1,3],x)
        self.assertEqual(after[[0,2]].tobytes(),p[[0,2]].tobytes())
        self.assertEqual(after[[1,3]].tolist(),[[.2,.3,.4],[.5,.6,.7]])
        for bad in [x[:-1],self.np.r_[x[:-1],self.np.nan]]:
            with self.assertRaises(ValueError):self.f['assemble_points'](self.np,p,[1,3],bad)

    def test_callback_uses_actual_strict_quality_not_t_or_residual(self):
        state={'quality_target_stop':False};values=[.099,.3]
        callback=self.f['quality_target_callback'](lambda x:self.np.array(values),2,state)
        self.assertFalse(callback([0.,0.,0.,100.],SimpleNamespace(constr_violation=0)))
        self.assertFalse(state['quality_target_stop'])
        values[:]=[.1,.3]
        self.assertTrue(callback([0.,0.,0.,100.],SimpleNamespace(constr_violation=100)))
        self.assertTrue(state['quality_target_stop'])
        for values,count in [([.1,float('nan')],2),([True,.2],2),([.2],2),([],0)]:
            self.assertFalse(self.f['all_quality_at_gate'](values,count))

    def test_status_three_requires_true_quality_stop_and_all_values(self):
        vector=[0.]*3295;gate=self.f['final_quality_gate']
        gate(True,1,False,vector,[.1,.2],2)
        gate(False,3,True,vector,[.1,.2],2)
        for args in [(False,3,False,vector,[.1,.2],2),(True,3,False,vector,[.1,.2],2),
                     (False,0,True,vector,[.1,.2],2),(True,1,False,vector,[.099,.2],2),
                     (False,3,True,vector,[.1,float('inf')],2),(True,1,False,vector[:-1],[.1,.2],2)]:
            with self.assertRaises(ValueError):gate(*args)

    def test_documented_warning_raises_before_simulated_dense_fallback(self):
        dense_called=[]
        with warnings.catch_warnings(record=True):
            self.f['refuse_documented_dense_fallback']()
            with self.assertRaises(UserWarning):
                warnings.warn('Singular Jacobian matrix. Using dense SVD decomposition to perform the factorizations.',UserWarning)
                dense_called.append(True)
        self.assertEqual(dense_called,[])

    def test_linear_objective_gradient_and_zero_sparse_shape(self):
        x=[0.]*3294+[.2]
        self.assertEqual(self.f['objective'](x),-.2)
        self.assertEqual(self.f['objective_gradient'](x),[0.]*3294+[-1.])
        class Sparse:
            @staticmethod
            def csr_matrix(shape,dtype):return ('emptyCSR',shape,dtype)
        self.assertEqual(self.f['zero_objective_hessian'](Sparse,x),('emptyCSR',(3295,3295),float))
        with self.assertRaises(ValueError):self.f['objective_gradient'](x[:-1])

    def test_diagnostic_coordinate_words_and_nonfinite_solver_metrics(self):
        rows=self.f['coordinate_rows']([17,29],[1,0],[[1.,2.,3.],[-0.,4.,5.]])
        self.assertEqual([r['node_tag'] for r in rows],[17,29]);self.assertEqual(rows[0]['binary64_hex'][0],'-0x0.0p+0')
        result=SimpleNamespace(success=False,status=3,nit=2,nfev=3,njev=1,message='callback',fun=float('nan'),optimality=.1,constr_violation=10.)
        meta=self.f['solver_metadata'](result,True)
        self.assertIsNone(meta['fun']);self.assertEqual(meta['nonfinite_reported_metrics'],{'fun':'nan'})
        self.assertEqual(meta['status'],3);self.assertTrue(meta['quality_target_stop'])

    def test_single_call_checkpoint_diagnostic_before_gate_and_separate_proposal(self):
        raw=(HERE/'sparse_head.py').read_text();tree=ast.parse(raw)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='minimize']
        self.assertEqual(len(calls),1);self.assertIn('callback',{k.arg for k in calls[0].keywords})
        main=raw[raw.index('def main():'):]
        self.assertLess(main.index("save(out/'solver-start-checkpoint.json'"),main.index('result=optimize.minimize'))
        self.assertLess(main.index("save(out/'solver-final-state.json',diagnostic)  # Always"),main.index('final_quality_gate('))
        self.assertLess(main.index('final_quality_gate('),main.index("save(out/'coordinate-proposal.json'"))
        self.assertIn("'962-expanded-SICN-solver-final-state-diagnostic/v1'",raw)
        self.assertIn("'962-direct-SICN-expanded-tagged-coordinate-proposal/v1'",raw)
        self.assertFalse(self.c['execution_authorized']);self.assertEqual(self.c['input_counts']['fixed_context_nodes'],10969)
        self.assertEqual(self.c['input_counts']['constraints'],29473)


if __name__=='__main__':unittest.main()
