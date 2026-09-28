import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile

HERE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
from trial_meshers_2026 import boundary,normalize_convention,read_inner_tets
from reconcile_volume_flux import BODY_SHA,SELECTED,METHODS,reconcile


class FluxCoverageTests(unittest.TestCase):
    def test_complete_coverage_is_required_and_patches_cannot_mask_bad_errors(self):
        base=dict(input_sha256=BODY_SHA,status='completed',inputs_unchanged=True,reference_point=[0,0,0],
            runs=[dict(epsilon=e,faces_private=[dict(face_index=i,**{m:dict(signed_flux=1.,estimated_relative_error=1e-14)
                for m in ('Gauss','GaussKronrod')}) for i in range(1,4919)]) for e in (1e-10,1e-12)])
        patches=[dict(input_sha256=BODY_SHA,status='completed',inputs_unchanged=True,witness_volume=24.,
            results=[dict(face_index=i,outer_method=m,inner_Gauss_order=n,signed_flux=1.,
                outer_estimated_absolute_error=1e-14 if m=='QUADPACK' else None) for m,n in METHODS]) for i in SELECTED]
        self.assertTrue(reconcile(base,patches)['numerical_agreement_passed'])
        patches[0]['witness_volume']=float('nan')
        with self.assertRaises(ValueError):reconcile(base,patches)
        patches[0]['witness_volume']=24.
        error_row=next(r for r in patches[0]['results'] if r['outer_method']=='QUADPACK')
        error_row['outer_estimated_absolute_error']=-1.
        with self.assertRaises(ValueError):reconcile(base,patches)
        error_row['outer_estimated_absolute_error']=1e-14
        base['runs'][0]['faces_private'][-1]['Gauss']['estimated_relative_error']=1.
        self.assertFalse(reconcile(base,patches)['numerical_agreement_passed'])
        base['runs'][0]['faces_private'].pop()
        with self.assertRaises(ValueError):reconcile(base,patches)


@unittest.skipUnless(importlib.util.find_spec('numpy'),'numpy is optional')
class OrientationTests(unittest.TestCase):
    def test_convention_is_uniform_not_a_local_inversion_repair(self):
        import numpy as np
        p=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        c=np.array([[0,1,2,3]])
        good,reverse=normalize_convention(p,c)
        self.assertFalse(reverse); self.assertEqual(len(boundary(good)),4)
        good,reverse=normalize_convention(p,c[:,[0,2,1,3]])
        self.assertTrue(reverse); self.assertTrue(np.array_equal(good,c))
        with self.assertRaises(ValueError): normalize_convention(p,np.array([[0,1,2,3],[0,2,1,3]]))
        with self.assertRaises(ValueError): normalize_convention(p,np.array([[0,1,2,2]]))
        with self.assertRaises(ValueError): boundary(np.repeat(c,3,axis=0))

    def test_classified_parser_excludes_outer_tetrahedra(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.tet'
            path.write_text('4 vertices\n1 inner tets\n1 outer tets\n0 0 0\n1 0 0\n0 1 0\n0 0 1\n4 0 1 2 3\n4 0 2 1 3\n')
            points,cells,counts=read_inner_tets(path)
            self.assertEqual(cells.tolist(),[[0,1,2,3]])
            self.assertEqual(counts['outer_tetrahedra_excluded'],1)
            path.write_text('4 vertices\n2 tets\n0 0 0\n')
            with self.assertRaises(ValueError):read_inner_tets(path)


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('scipy'),
                     'isolated OCP 8 / SciPy runtime is optional')
class FluxTests(unittest.TestCase):
    def test_bilinear_surface_crosses_a_knot_and_preserves_reversed_orientation(self):
        import OCP
        if OCP.__version__!='8.0.1.0': self.skipTest('requires OCP 8.0.1.0')
        from OCP.collections import Array2_gp_Pnt,Array1_double,Array1_int
        from OCP.gp import gp_Pnt
        from OCP.Geom import Geom_BSplineSurface
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.TopoDS import TopoDS
        from integrate_trimmed_flux import integrate_face
        poles=Array2_gp_Pnt(1,2,1,3)
        for i,x in enumerate((0.,1.),1):
            for j,y in enumerate((0.,.5,1.),1):poles.SetValue(i,j,gp_Pnt(x,y,1+x*y))
        def array(kind,values):
            a=kind(1,len(values))
            for i,v in enumerate(values,1):a.SetValue(i,v)
            return a
        surface=Geom_BSplineSurface(poles,array(Array1_double,[0.,1.]),array(Array1_double,[0.,.5,1.]),
            array(Array1_int,[2,2]),array(Array1_int,[2,1,2]),1,1)
        face=BRepBuilderAPI_MakeFace(surface,1e-10).Face()
        # Integral (1-u*v)/3 over the unit parameter square is 1/4.
        for order,adaptive in ((16,False),(32,True)):
            self.assertAlmostEqual(integrate_face(face,order,adaptive)['signed_flux'],.25,places=12)
            self.assertAlmostEqual(integrate_face(TopoDS.Face(face.Reversed()),order,adaptive)['signed_flux'],-.25,places=12)


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('scipy'),
                     'NumPy / SciPy runtime is optional')
class RegionTests(unittest.TestCase):
    def test_disconnected_tetrahedra_are_not_deleted(self):
        import numpy as np
        try:
            from scipy.sparse import coo_matrix
        except ImportError:
            self.skipTest('optional compiled SciPy sparse runtime is unavailable; exercise on Linux')
        from audit_envelope_regions import audit
        tet=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        result,labels=audit(np.concatenate([tet,tet+3]),np.array([[0,1,2,3],[4,5,6,7]]))
        self.assertEqual(result['tetra_components'],2)
        self.assertEqual(sorted(labels.tolist()),[0,1])
        self.assertEqual(result['boundary_edges_not_incident_twice'],0)
        self.assertEqual(result['boundary_edges_with_unbalanced_orientation'],0)
        self.assertAlmostEqual(sum(r['volume'] for r in result['regions']),1/3)


if __name__=='__main__': unittest.main()
