"""Prepared stdlib guards; no scientific import or actual native output read."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
import assess_cube as M


class Guards(unittest.TestCase):
    def test_actual_direct_pin_guard_requires_log_and_native_contract(self):
        import ast
        tree=ast.parse(Path(M.__file__).read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='assess')
        start=next(i for i,n in enumerate(function.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='required' for t in n.targets))
        guard=function.body[start:start+3]
        self.assertIsInstance(guard[1],ast.For)
        self.assertIn('All consumed fields',ast.unparse(guard[2]))
        code=compile(ast.Module(body=guard,type_ignores=[]),'actual-direct-pin-guard','exec')
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d).resolve();fields=['Exodus_file','nodal_CSV','fields_CSV','operator','preconditioner','rhs','correction','ksp']
            c={key:str(directory/key) for key in fields+['card','reference','primary_side_source']}
            source=str(directory/'assess_cube.py');receipt=str(directory/'native-execution.json')
            pins=[source,receipt,str(directory/'native.log'),str(directory/'frozen-contract.json'),*[c[k] for k in fields+['card','reference','primary_side_source']]]
            native={'artifact_sha256':{Path(c[k]).name:'a'*64 for k in fields}}
            for missing in [None,'native.log','frozen-contract.json']:
                context={**c,'input_sha256':{p:'a'*64 for p in pins if missing is None or Path(p).name!=missing}}
                namespace={'c':context,'native':native,'directory':directory,'__file__':source,'str':str,'Path':Path,'need':M.need}
                if missing is None:exec(code,namespace)
                else:
                    with self.subTest(missing=missing),self.assertRaisesRegex(ValueError,'direct-pinned'):exec(code,namespace)

    def test_nodal_complete_coordinate_join_and_refusals(self):
        coords=[(0.,0.,0.),(1.,0.,0.)]
        rows=[dict(id=str(10-i),x=str(p[0]),y=str(p[1]),z=str(p[2]),**{k:'0' for k in M.DISP+M.FORCE}) for i,p in enumerate(coords)]
        result=M.node_values(list(reversed(rows)),coords)
        self.assertEqual(result[M.bits(coords[0])]['observed_id'],10)
        for change in ['duplicate','fractional','nonfinite','missing','signedzero']:
            bad=copy.deepcopy(rows)
            if change=='duplicate':bad[1]['id']=bad[0]['id']
            elif change=='fractional':bad[0]['id']='1.5'
            elif change=='nonfinite':bad[0]['disp_x']='nan'
            elif change=='missing':del bad[0]['rz']
            else:bad[0]['x']='-0.0'
            with self.subTest(change=change),self.assertRaises(ValueError):M.node_values(bad,coords)

    def test_complete_qp0_centroid_join_and_refusals(self):
        centers=[(0.,0.,0.),(1.,0.,0.)]
        rows=[dict(elem_id=str(20-i),qp_id='0',x=str(p[0]),y=str(p[1]),z=str(p[2]),**{f'{prefix}_{s}':'0' for prefix in ['stress','total_strain'] for s in ['xx','yy','zz','xy','xz','yz']}) for i,p in enumerate(centers)]
        joined=M.join_qp(list(reversed(rows)),centers,1e-12)
        self.assertEqual(joined[0]['elem_id'],'20')
        for change in ['missing','duplicate','qp1','ambiguous','nonfinite']:
            bad=copy.deepcopy(rows);c=centers
            if change=='missing':bad.pop()
            elif change=='duplicate':bad[1]['elem_id']=bad[0]['elem_id']
            elif change=='qp1':bad[0]['qp_id']='1'
            elif change=='ambiguous':c=[centers[0],centers[0]]
            else:bad[0]['x']='inf'
            with self.subTest(change=change),self.assertRaises(ValueError):M.join_qp(bad,c,1e-12)

    def test_unit_tetra_affine_reactions_energy_and_even_permutation(self):
        p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        u=[(.01*x,.02*y,.03*z) for x,y,z in p]
        V,eps,stress,forces,U=M.p1_cell(p,u,0.,50.)
        self.assertEqual(V,1/6)
        for i in range(3):self.assertAlmostEqual(stress[i][i],i+1)
        expected=[[-1/6,-2/6,-3/6],[1/6,0,0],[0,2/6,0],[0,0,3/6]]
        for got,want in zip(forces,expected):
            for a,b in zip(got,want):self.assertAlmostEqual(a,b)
        self.assertAlmostEqual(U,.5*(.01+.04+.09)/6)
        self.assertAlmostEqual(sum(M.dot(a,b) for a,b in zip(u,forces)),2*U)
        order=[1,2,0,3];other=M.p1_cell([p[i] for i in order],[u[i] for i in order],0.,50.)
        self.assertAlmostEqual(other[-1],U)
        for got,i in zip(other[-2],order):
            for a,b in zip(got,forces[i]):self.assertAlmostEqual(a,b)

    def test_rigid_translation_rotation_zero_energy(self):
        p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        for u in [[(2.,3.,4.)]*4,[(-y,x,0.) for x,y,z in p]]:
            out=M.p1_cell(p,u,10.,20.)
            self.assertEqual(out[-1],0.)
            self.assertTrue(all(x==0 for row in out[-2] for x in row))

    def test_invalid_tetra_refusals(self):
        p=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)];u=[(0.,0.,0.)]*4
        for q in [[p[0],p[2],p[1],p[3]],[p[0],p[1],p[2],p[2]]]:
            with self.assertRaises(ValueError):M.p1_cell(q,u,10.,20.)

    def test_45row_algebra_sign_residual_and_preconditioner(self):
        A=[[0.]*45 for _ in range(45)]
        for i in range(45):A[i][i]=1. if i<24 else 2.
        P=copy.deepcopy(A);y=[-(i+1)/1000 for i in range(45)];F=[A[i][i]*y[i] for i in range(45)]
        result=M.algebra(A,P,F,y,1e-10)
        self.assertEqual(len(result['identity_rows']),24)
        self.assertFalse(result['full_node_to_PETSc_row_map_established'])
        for kind in ['sign','missing','P','nan','identity']:
            a,p,f,v=copy.deepcopy((A,P,F,y))
            if kind=='sign':v=[-x for x in v]
            elif kind=='missing':v.pop()
            elif kind=='P':p[44][44]+=1
            elif kind=='nan':v[0]=math.nan
            else:a[44][44]=1.;p[44][44]=1.;f[44]=v[44]
            with self.subTest(kind=kind),self.assertRaises(ValueError):M.algebra(a,p,f,v,1e-10)

    def test_numeric_export_parser_rejects_torn_or_executable_text(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'vector.m';p.write_text('v=[\n-1\n-2\n];\n')
            self.assertEqual(M.blocks(p,1),[[[-1.],[-2.]]])
            for text in ['v=[\n-1\n','v=[\n__import__("os")\n];','v=[\nnan\n];']:
                p.write_text(text)
                with self.assertRaises(ValueError):M.blocks(p,1)

    def test_actual_solver_profile_rejects_duplicate_or_wrong_cycle(self):
        text='type: gmres\ntype: hypre\nHYPRE BoomerAMG preconditioning\nCycle type V\nMaximum number of iterations PER hypre call 1\nConvergence tolerance PER hypre call 0\n'
        self.assertEqual(M.actual_settings(text)['maximum_iterations_per_PC_call'],1)
        for bad in [text+'type: gmres\n',text.replace('type V','type W'),text.replace('hypre call 1','hypre call 2')]:
            with self.assertRaises(ValueError):M.actual_settings(bad)


if __name__=='__main__':unittest.main()
