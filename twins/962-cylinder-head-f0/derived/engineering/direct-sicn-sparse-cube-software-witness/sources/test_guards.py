"""ROOT-ONLY NumPy literal guards; author did not run/import NumPy/SciPy/Gmsh.

AST-extract the actual kernel/mapping only. No SciPy, Gmsh, optimizer or head rows.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
SOURCE_SHA256='2ef99ee727f74ca7cc672f8e106f804d89cb5c41eb86b643b423913841ea4ed7'
TINY_SHA256='8351733aa0cd3dff2c86bcedd6c5cf931fde7306d0870738f9794448fbe8d12e'
TINY_REPORT_SHA256='0512708595378fe0d316de08305c35f98138b082a2deb83bdb60717783cd8058'


def extracted(path,digest,names,namespace):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Frozen source changed')
    tree=ast.parse(data); body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in body}!=set(names):raise ValueError('Exact helper set required')
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),namespace)
    return namespace


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c=json.loads((HERE/'held-contract.json').read_text())
        import numpy as np  # Root-authorized literal arithmetic only; no scientific import by author.
        if np.__version__!='2.2.6' or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve():
            raise ValueError('Selected NumPy version/origin required')
        if hashlib.sha256(Path(c['numpy_init']).read_bytes()).hexdigest()!=c['runtime_files'][c['numpy_init']]:
            raise ValueError('Selected NumPy source pin changed')
        cls.np=np
        cls.f=extracted(HERE/'sparse_cube.py',SOURCE_SHA256,
                       ['signed_sicn_vector','tagged_indices','assemble_points'],{'math':math})
        cls.scalar=extracted(Path(c['tiny_scalar_source']),TINY_SHA256,
                             ['sub','dot','cross','signed_sicn'],{'math':math})['signed_sicn']
        cls.c=c

    def test_regular_sliver_reversed_and_planar_sign(self):
        regular=((0.,0.,0.),(1.,0.,0.),(.5,math.sqrt(3.)/2.,0.),(.5,math.sqrt(3.)/6.,math.sqrt(2./3.)))
        sliver=tuple((x,y,z*.001) for x,y,z in regular)
        reversed_cell=(regular[1],regular[0],regular[2],regular[3])
        planar=tuple((x,y,0.) for x,y,z in regular)
        values=self.f['signed_sicn_vector'](self.np,[regular,sliver,reversed_cell])
        for p,q in zip([regular,sliver,reversed_cell],values):
            self.assertTrue(math.isclose(float(q),type(self).scalar(p),rel_tol=1e-11,abs_tol=1e-14))
        self.assertGreater(values[0],0);self.assertGreater(values[1],0);self.assertLess(values[2],0)
        self.assertEqual(float(self.f['signed_sicn_vector'](self.np,[planar],True)[0]),0.)
        with self.assertRaises(ValueError):self.f['signed_sicn_vector'](self.np,[planar])

    def test_nonfinite_collapsed_shape_and_overflow_refuse(self):
        good=self.np.array([[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]])
        for bad in [self.np.zeros((1,4,3)),good*self.np.inf,good*1e300,good[:,0],good.astype(bool)]:
            with self.assertRaises(ValueError):self.f['signed_sicn_vector'](self.np,bad)

    def test_all_saved_tiny_native_rows_and_scalar(self):
        path=Path(self.c['tiny_native_report'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),TINY_REPORT_SHA256)
        d=json.loads(path.read_text())
        for key in ['before','centre_reference','after','saved']:
            row=d[key];lookup=dict(zip(row['node_tags'],row['coordinates_mm']))
            cells=[[lookup[t] for t in cell] for cell in row['connectivity']]
            actual=self.f['signed_sicn_vector'](self.np,cells)
            self.assertEqual(len(actual),12)
            for p,q,native in zip(cells,actual,row['qualities']['minSICN']):
                self.assertTrue(math.isclose(float(q),native,rel_tol=1e-11,abs_tol=1e-14))
                self.assertTrue(math.isclose(float(q),type(self).scalar(p),rel_tol=1e-11,abs_tol=1e-14))

    def test_shared_tag_mapping_and_unselected_raw_bits(self):
        tags=[11,19,23,29,31];cells=[[11,19,23,31],[11,23,29,31]]
        idx,pos=self.f['tagged_indices'](tags,cells,[19,31])
        self.assertEqual(idx,[[0,1,2,4],[0,2,3,4]]);self.assertEqual(pos,[1,4])
        original=self.np.arange(15,dtype='f8').reshape((5,3));original[0,0]=-0.;original.setflags(write=False)
        x=self.np.array([.1,.2,.3,.4,.5,.6,.7]);out=self.f['assemble_points'](self.np,original,pos,x)
        self.assertEqual(out[[0,2,3]].tobytes(),original[[0,2,3]].tobytes())
        self.assertEqual(out[pos].tolist(),[[.1,.2,.3],[.4,.5,.6]])
        for bad in [x[:-1],self.np.r_[x[:-1],self.np.nan]]:
            with self.assertRaises(ValueError):self.f['assemble_points'](self.np,original,pos,bad)

    def test_duplicate_unknown_and_movable_tag_refusals(self):
        for tags,cells,movable in [([1,1,2,3],[[1,2,3,4]],[2]),([1,2,3,4],[[1,2,3,9]],[2]),
                ([1,2,3,4],[[1,2,3,4]],[9]),([1,2,3,4],[[1,2,2,4]],[2]),([1,2,3,4],[[1,2,3,4]],[2,2])]:
            with self.assertRaises(ValueError):self.f['tagged_indices'](tags,cells,movable)

    def test_single_solver_call_and_held_scope(self):
        tree=ast.parse((HERE/'sparse_cube.py').read_text());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        minimize=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='minimize']
        self.assertEqual(len(minimize),1);self.assertEqual({k.arg for k in minimize[0].keywords},{'method','jac','hess','bounds','constraints','options'})
        self.assertEqual(self.c['solver'],dict(method='trust-constr',maxiter=100,gtol=1e-8,xtol=1e-10,barrier_tol=1e-10,finite_diff_rel_step=2.**-26,sparse_jacobian=True,factorization_method='AugmentedSystem'))
        self.assertFalse(self.c['execution_authorized']);self.assertEqual(self.c['sicn_gate'],.1)
        constraint=next(n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='NonlinearConstraint')
        kw={k.arg:k.value for k in constraint.keywords};self.assertEqual(ast.literal_eval(kw['jac']),'2-point')
        self.assertIn('finite_diff_jac_sparsity',kw);self.assertIn('finite_diff_rel_step',kw)
        self.assertEqual(ast.unparse(kw['hess']),'optimize.BFGS()')
        self.assertNotIn('eps',self.c['solver']);self.assertNotIn('ftol',self.c['solver'])
        self.assertTrue(any(isinstance(n.func,ast.Attribute) and n.func.attr=='catch_warnings' for n in calls))
        self.assertIn("warnings.simplefilter('always')",(HERE/'sparse_cube.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Import) and any(a.name=='gmsh' for a in n.names) for n in ast.walk(tree)))


    def tiny_helpers(self):
        return extracted(HERE/'sparse_cube.py',SOURCE_SHA256,['tagged_indices','jacobian_entries','objective','objective_gradient','zero_objective_hessian','final_quality_gate'],{'math':math,'GATE':.1})

    def test_exact_corner_epigraph_sparsity_shared_and_fixed_corners(self):
        f=self.tiny_helpers();rows,cols,shape=f['jacobian_entries']([11,19,23,29,31],[[11,19,23,31],[11,23,29,31]],[19,31])
        self.assertEqual(shape,(2,7));self.assertEqual([(i,j) for i,j in zip(rows,cols)],[(0,j) for j in range(7)]+[(1,j) for j in [3,4,5,6]])
        tiny=ast.parse((HERE/'sparse_cube.py').read_text());ns={}
        names={'NODE_TAGS','TET_TAGS','TRI_TAGS','BOUNDARY','TRIANGLES','TETS','INITIAL','CENTRE'}
        constants=[n for n in tiny.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
        exec(compile(ast.Module(body=constants,type_ignores=[]),'literal constants','exec'),ns)
        r,c,shape=f['jacobian_entries'](list(ns['NODE_TAGS']),[list(v) for v in ns['TETS']],[201])
        self.assertEqual(shape,(12,4));self.assertEqual(len(r),48)
        self.assertEqual(list(zip(r,c)),[(i,j) for i in range(12) for j in range(4)])

    def test_linear_objective_exact_gradient_zero_sparse_Hessian(self):
        f=self.tiny_helpers();x=[.25,-.5,1.,.3]
        self.assertEqual(f['objective'](x),-.3);self.assertEqual(f['objective_gradient'](x),[0.,0.,0.,-1.])
        class Sparse:
            @staticmethod
            def csr_matrix(shape,dtype):return dict(shape=shape,nnz=0,dtype=dtype)
        h=f['zero_objective_hessian'](Sparse,x);self.assertEqual(h,dict(shape=(4,4),nnz=0,dtype=float))
        for i in range(4):
            y=list(x);y[i]+=2.**-10
            self.assertEqual(f['objective'](y)-f['objective'](x),f['objective_gradient'](x)[i]*2.**-10)
        with self.assertRaises(ValueError):f['objective_gradient']([1.])

    def test_final_all12_finite_quality_not_solver_success_or_epigraph_only(self):
        f=self.tiny_helpers();good=[.2]*12;f['final_quality_gate'](True,[0.,0.,0.,.2],good)
        for success,x,q in [(False,[0.,0.,0.,.2],good),(True,[0.,0.,0.,.9],[.099]+good[1:]),(True,[0.,0.,0.,float('nan')],good),(True,[0.,0.,0.,.2],good[:11]),(True,[0.,0.,0.,.2],[float('inf')]+good[1:])]:
            with self.assertRaises(ValueError):f['final_quality_gate'](success,x,q)


if __name__=='__main__':unittest.main()
