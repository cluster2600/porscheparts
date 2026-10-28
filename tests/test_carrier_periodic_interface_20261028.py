"""Check complete periodic boundary bijections and a sufficient whole-T10 mapping bound."""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/periodic_interface_mesh.py'
spec=importlib.util.spec_from_file_location('periodic_interface',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class InterfaceMeshTests(unittest.TestCase):
    def grid(self):return np.array([[x,y,z]for z in [-.5,0,.5]for y in [-.5,0,.5]for x in [-.5,0,.5]])

    def test_periodicity_checks_boundaries_and_ignores_interior_node_distribution(self):
        x=self.grid();x[13]=[.17,.22,-.13];np.random.default_rng(993).shuffle(x)
        self.assertEqual(len(m.audit_periodicity(x)),3)

    def test_both_signs_of_boundary_drift_are_rejected(self):
        for shift in [-1e-5,1e-5]:
            x=self.grid();x[14,1]+=shift
            with self.assertRaises(ValueError):m.audit_periodicity(x)

    def test_missing_duplicate_and_looser_boundary_contracts_are_rejected(self):
        x=self.grid()
        for bad in [x[:-1],np.vstack([x,x[14]])]:
            with self.assertRaises(ValueError):m.audit_periodicity(bad)
        with self.assertRaises(ValueError):m.audit_periodicity(x,1e-5)

    def tetra(self):
        x=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        return np.vstack([x,[(x[a]+x[b])/2 for a,b in m.EDGES]])

    def test_affine_quadratic_tetrahedron_has_zero_perturbation_and_correct_volume(self):
        r=m.audit_t10(self.tetra(),np.arange(10)[None,:]);self.assertEqual(r['whole_simplex_relative_Jacobian_bound'],0.);self.assertAlmostEqual(r['volume_mm3'],1/6)

    def test_inverted_corners_wrong_order_and_large_midpoint_warp_are_rejected(self):
        for kind in ['inverted','order','warp']:
            x=self.tetra()
            if kind=='inverted':x[[1,2]]=x[[2,1]]
            elif kind=='order':x[[8,9]]=x[[9,8]]
            else:x[4,0]+=1
            with self.assertRaises(ValueError):m.audit_t10(x,np.arange(10)[None,:])

    def test_periodic_triangle_connectivity_is_checked_in_addition_to_node_positions(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from periodic_interface_topology import audit_facets
        finally:sys.path.pop(0)
        points=[];ids={};cells=[]
        def node(x):
            key=tuple(x)
            if key not in ids:ids[key]=len(points);points.append(x.copy())
            return ids[key]
        for order in itertools.permutations(range(3)):
            corners=np.vstack([np.zeros(3),np.eye(3)[order[0]],np.eye(3)[order[0]]+np.eye(3)[order[1]],np.ones(3)])-.5
            if np.linalg.det((corners[1:]-corners[0]).T)<0:corners[[1,2]]=corners[[2,1]]
            cells.append([node(x)for x in corners]+[node((corners[a]+corners[b])/2)for a,b in m.EDGES])
        points=np.array(points);cells=np.array(cells);m.audit_periodicity(points);r=audit_facets(points,cells)
        self.assertEqual([x['opposite_T6_face_pairs']for x in r['opposite_faces']],[2,2,2])
        with self.assertRaises(ValueError):audit_facets(points,cells[:-1])
        # Geometrically coincident interior midsides with distinct IDs break C0 continuity.
        split=points[cells[0,7]].copy();broken=cells.copy();broken[0,7]=len(points)
        doubled=np.vstack([points,split]);m.audit_periodicity(doubled);m.audit_t10(doubled,broken)
        with self.assertRaisesRegex(ValueError,'Interior T6'):audit_facets(doubled,broken)

    def test_CalculiX_numeric_fields_keep_precision_within_the_native_width_limit(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from periodic_interface_mechanics import ccx_number
        finally:sys.path.pop(0)
        values=[-0.099999999999999978,0.019615242270663139,3.3306690738754701e-16,-.5,.001,0.]
        for x in values:
            text=ccx_number(x);self.assertLessEqual(len(text),20);self.assertAlmostEqual(float(text),x,delta=max(abs(x)*5e-13,1e-30))
        for x in [float('nan'),float('inf')]:
            with self.assertRaises(ValueError):ccx_number(x)

    def test_series_requires_two_true_refinements_of_one_geometry_and_six_cases(self):
        import copy
        sys.path.insert(0,str(SOURCE.parent))
        try:from assess_interface_series import compare_levels
        finally:sys.path.pop(0)
        # Synthetic tensors test the admission rule, not numerical solver qualification.
        rows=[dict(STEP_sha256='fixed',transport_sha256=str(i),tetrahedra=100*2**i,
                   maximum_edge_mm=1/(i+1),mechanics=dict(cases=[dict(mode=j)for j in range(6)],
                   effective_C_MPa=(np.eye(6)*v).tolist()))for i,v in enumerate([1.,1.01,1.02])]
        self.assertTrue(compare_levels(rows)['fixed_geometry_h_converged'])
        bad=copy.deepcopy(rows);bad[2]['mechanics']['effective_C_MPa']=(np.eye(6)*1.1).tolist()
        self.assertFalse(compare_levels(bad)['fixed_geometry_h_converged'])
        for kind in ['geometry','replay','weak','edge','partial']:
            bad=copy.deepcopy(rows)
            if kind=='geometry':bad[2]['STEP_sha256']='other'
            elif kind=='replay':bad[2]['transport_sha256']=bad[1]['transport_sha256']
            elif kind=='weak':bad[2]['tetrahedra']=210
            elif kind=='edge':bad[2]['maximum_edge_mm']=.5
            else:bad[2]['mechanics']['cases'].pop()
            with self.assertRaises(ValueError):compare_levels(bad)

    def test_core_face_connectivity_distinguishes_face_edge_and_vertex_contacts(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from inspect_selected_core import face_components
        finally:sys.path.pop(0)
        number,_,bad=face_components(np.array([[0,1,2,3],[0,1,2,4]]))
        self.assertEqual((number,bad),(1,0))
        number,_,bad=face_components(np.array([[0,1,2,3],[0,1,4,5]]))
        self.assertEqual((number,bad),(2,1))
        number,_,bad=face_components(np.array([[0,1,2,3],[0,4,5,6]]))
        self.assertEqual((number,bad),(2,0))
        for cells in [np.array([[0,1,2,3],[0,1,2,3]]),np.array([[0,1,2,3],[0,1,2,4],[0,1,2,5]])]:
            with self.assertRaises(ValueError):face_components(cells)
