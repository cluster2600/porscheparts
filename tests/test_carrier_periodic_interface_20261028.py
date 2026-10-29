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
    def test_variant_oracle_rejects_indices_before_narrowing_to_int32(self):
        import hashlib
        import json
        import subprocess
        import tempfile
        if importlib.util.find_spec('igl') is None:self.skipTest('libigl oracle runtime is unavailable')
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary)
            for index,faces in enumerate([np.array([[0,1,2**32+2]],dtype=np.uint64),np.array([[0,1,2.5]]),np.array([[0,1,-1]])]):
                directory=root/str(index);directory.mkdir();archive=directory/'candidate.npz'
                np.savez(archive,vertices=np.array([[0.,0,0],[1,0,0],[0,1,0]]),triangles=faces)
                record=dict(status='complete_closed_chamber_variant_geometry_checked',manufacturing_authorized=False,
                            output_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),vertices=3,triangles=1,
                            original_external_oriented_triangles_exact=True,final_oriented_triangle_roundtrip_exact=True)
                (directory/'assessment.json').write_text(json.dumps(record))
                result=subprocess.run([sys.executable,str(SOURCE.with_name('prepare_carrier_warp_oracle.py')),
                                       '--variant-directory',str(directory),'--output',str(root/('output-'+str(index)))],
                                      capture_output=True,text=True,timeout=30)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('bounded integer triangle indices required',result.stderr)

    def test_triangle_witness_checks_interior_edges_and_collapsed_faces(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from finite_gyroid_voids import triangle_witness_distance
        finally:sys.path.pop(0)
        tri=np.array([[[0.,0,0],[1,0,0],[0,1,0]]])
        for point,expected in [([.25,.25,0],0),([.5,0,2],2),([2,0,0],1)]:
            self.assertAlmostEqual(float(triangle_witness_distance([point],tri)[0]),expected)
        collapsed=np.zeros((1,3,3))
        self.assertEqual(float(triangle_witness_distance([[0,0,2]],collapsed)[0]),2)

    def test_skinny_cap_triangle_has_an_actual_edge_witness(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from finite_gyroid_voids import triangle_witness_distance
        finally:sys.path.pop(0)
        tri=np.array([[[-69.87200178303081,31.73488615113345,-.26375403832963223],
                       [-68.9486955739393,29.80531336721438,1.4997774011607232],
                       [-68.94862800845094,29.80525619462985,1.4997708718466203]]])
        point=[[-69.4959124255063,30.948949501663773,.4545281662395994]]
        self.assertLess(float(triangle_witness_distance(point,tri)[0]),1e-10)

    def test_finite_volume_series_keeps_mechanics_and_topology_separate(self):
        import copy
        sys.path.insert(0,str(SOURCE.parent))
        try:from assess_finite_voids import compare
        finally:sys.path.pop(0)
        parameters=dict(finite_sizes_mm=[.25,.125,.0625],maximum_relative_volume_change=.02,required_successive_volume_comparisons=2)
        levels=[dict(rank=0,size_mm=h,core_volume_mm3=10.,source_sha256='same',void_volume_mm3=v)for h,v in zip(parameters['finite_sizes_mm'],[5.,5.005,5.006])]
        self.assertTrue(compare(levels,parameters)['volume_stabilized'])
        bad=copy.deepcopy(levels);bad[0]['void_volume_mm3']=4.
        self.assertFalse(compare(bad,parameters)['volume_stabilized'])
        for field,value in [('size_mm',.25),('source_sha256','different'),('core_volume_mm3',11.)]:
            bad=copy.deepcopy(levels);bad[1][field]=value
            with self.assertRaises(AssertionError):compare(bad,parameters)

    def test_full_clip_search_finds_the_adjacent_triangle_witness(self):
        import json
        sys.path.insert(0,str(SOURCE.parent))
        try:from finite_gyroid_voids import triangle_witness_distance
        finally:sys.path.pop(0)
        fixture=SOURCE.parents[5]/'docs/reports/carrier-interface-20261028/evidence/finite-gyroid-001/distance-diagnostics/adjacent-triangle-regression.json'
        r=json.loads(fixture.read_text());tri=np.array([r['initial_candidate_triangle_mm'],r['adjacent_witness_triangle_mm']]);points=np.tile(r['point_mm'],(2,1));d=triangle_witness_distance(points,tri)
        self.assertGreater(float(d[0]),r['classification_limit_mm'])
        self.assertLess(float(d.min()),1e-10)

    def test_exact_binary64_triangle_distance_is_rational(self):
        from fractions import Fraction
        sys.path.insert(0,str(SOURCE.parent))
        try:from network_gap_witnesses import exact_squared_distance
        finally:sys.path.pop(0)
        triangle=[[0,0,0],[1,0,0],[0,1,0]]
        self.assertEqual(exact_squared_distance([.25,.25,2],triangle),Fraction(4))
        self.assertEqual(exact_squared_distance([2,0,0],triangle),Fraction(1))
        self.assertEqual(exact_squared_distance([0,0,.5],[[0,0,0]]*3),Fraction(1,4))

    def test_whole_face_phase_bound_subdivides_and_respects_pitch(self):
        import math
        sys.path.insert(0,str(SOURCE.parent))
        try:from network_gap_witnesses import phase_boundary_bound
        finally:sys.path.pop(0)
        centre=np.ones(3)*(.5*math.asin(2*.6170021750539874/3))*10/(2*math.pi)
        vertices=centre+np.array([[.3,-.3,0],[0,.3,-.3],[-.3,0,.3]])
        r=phase_boundary_bound(vertices,np.array([[0,1,2]]),1,10.)
        self.assertTrue(r['passed']);self.assertGreater(r['subdivision_depth'],0)
        self.assertFalse(r['formal_interval_certificate'])
        self.assertFalse(phase_boundary_bound(vertices*.6,np.array([[0,1,2]]),1,6.)['passed'])

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

    def test_oriented_surface_roundtrip_ignores_order_but_rejects_winding_or_position_changes(self):
        sys.path.insert(0,str(SOURCE.parent))
        try:from reconstruct_core_envelopes import canonical_surface
        finally:sys.path.pop(0)
        vertices=self.tetra()[:4];faces=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        a,b=canonical_surface(vertices,faces)
        order=np.array([2,0,3,1]);inverse=np.argsort(order)
        c,d=canonical_surface(vertices[order],np.roll(inverse[faces[::-1]],1,axis=1))
        self.assertTrue(np.array_equal(a,c) and np.array_equal(b,d))
        reversed_faces=faces.copy();reversed_faces[0]=reversed_faces[0,::-1]
        self.assertFalse(np.array_equal(b,canonical_surface(vertices,reversed_faces)[1]))
        moved=vertices.copy();moved[0,0]+=1e-8
        self.assertFalse(np.array_equal(a,canonical_surface(moved,faces)[0]))

    def test_published_evidence_integrity_and_qualification_scope(self):
        import hashlib,json
        root=SOURCE.parents[5]
        # Publication integrity and scope checks are separate from native numerical execution.
        report=root/'docs/reports/carrier-interface-20261028/evidence'
        for path,expected in json.loads((report/'publication-manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),expected,path)
        series=json.loads((report/'fixed-STEP-series-001/assessment.json').read_text())
        self.assertTrue(series['fixed_geometry_h_converged'])
        self.assertFalse(series['carrier_convergence_demonstrated'])
        self.assertFalse(series['implicit_geometry_convergence_demonstrated'])
        closed=json.loads((report/'closed-carrier-001/assessment.json').read_text())
        self.assertTrue(closed['candidate_geometry_generated'])
        self.assertTrue(closed['original_external_oriented_triangles_exact'])
        self.assertTrue(closed['final_oriented_triangle_roundtrip_exact'])
        self.assertLessEqual(closed['nominal_candidate_mass_kg'],1.3)
        self.assertEqual((closed['positive_material_shells'],closed['negative_void_shells']),(1,8))
        for key in ['baseline_geometry_changed','smooth_transitions_generated','powder_escape_demonstrated','complete_carrier_mechanics_converged','manufacturing_authorized']:
            self.assertFalse(closed[key],key)
        core=json.loads((report/'core-envelopes-006/assessment.json').read_text())
        self.assertFalse(core['carrier_geometry_changed'])
        self.assertFalse(core['cellular_carrier_generated'])
        self.assertFalse(core['manufacturing_authorized'])
        self.assertEqual(len(core['components']),4)
        for part in core['components']:
            self.assertEqual(part['native_components'],1)
            self.assertTrue(part['exact_oriented_triangle_roundtrip'])
            self.assertGreaterEqual(part['clearance']['floating_point_whole_boundary_clearance_lower_bound_mm'],.0001)
            self.assertFalse(part['clearance']['formal_interval_certificate'])
