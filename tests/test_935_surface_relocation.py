"""Independent local controls for the private surface-relocation continuation."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'twins/935-horizontal-cooling-system-f0/source/local-relocation-study-20261022'
try:
    import numpy as np
    spec=importlib.util.spec_from_file_location('surface_relocation',SOURCE/'surface_relocation.py')
    relocation=importlib.util.module_from_spec(spec);spec.loader.exec_module(relocation)
    spec=importlib.util.spec_from_file_location('graded_size',SOURCE/'graded_size.py')
    graded=importlib.util.module_from_spec(spec);spec.loader.exec_module(graded)
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


class RelocationSourceTests(unittest.TestCase):
    def test_shared_functions_match_the_executed_private_source(self):
        path=SOURCE/'propose-relocation-001.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'979aedded4acef24c823df800c5a815332cbbd2570910f363f886a00371da136')
        functions=lambda p:{node.name:ast.dump(node) for node in ast.parse(p.read_text()).body if isinstance(node,ast.FunctionDef)}
        self.assertEqual(functions(path),functions(SOURCE/'surface_relocation.py'))


@unittest.skipUnless(AVAILABLE,'Requires NumPy and SciPy')
class TangentialProposalTests(unittest.TestCase):
    def setUp(self):
        self.points=np.array([[0.,0,0],[1,0,0],[0,.001,0]])
        self.faces=np.array([[0,1,2]])

    def test_planar_skinny_triangle_improves_without_leaving_its_plane_or_radius(self):
        points=self.points.copy();faces=self.faces.copy()
        point=relocation.proposal(points,faces,2,.05)
        self.assertIsNotNone(point)
        self.assertEqual(point[2],0)
        self.assertLessEqual(np.linalg.norm(point-points[2]),.05+5e-7)
        triangle=np.array([[points[0],points[1],point]])
        self.assertGreater(relocation.qualities(triangle)[0][0],.05)
        np.testing.assert_array_equal(points,self.points);np.testing.assert_array_equal(faces,self.faces)

    def test_good_incident_triangle_keeps_its_quality_floor(self):
        points=np.vstack([self.points,[[-1.,0,0],[0,-1.,0]]]);faces=np.array([[0,1,2],[2,3,4]])
        point=relocation.proposal(points,faces,2,.05)
        self.assertIsNotNone(point)
        before,normals=relocation.qualities(points[faces]);changed=points.copy();changed[2]=point
        after,new_normals=relocation.qualities(changed[faces])
        self.assertTrue(np.all(after>=np.minimum(before,.05)))
        self.assertTrue(np.all(np.einsum('ij,ij->i',normals,new_normals)>0))

    def test_curved_fan_move_obeys_the_local_bound_without_claiming_surface_projection(self):
        angles=np.array([0.,.005,np.pi/2,np.pi,3*np.pi/2]);r=.1
        points=np.vstack([[0.,0,1],np.column_stack([r*np.cos(angles),r*np.sin(angles),np.full(len(angles),np.sqrt(1-r*r))])])
        faces=np.array([[0,i+1,(i+1)%len(angles)+1] for i in range(len(angles))])
        point=relocation.proposal(points,faces,0,.01)
        self.assertIsNotNone(point)
        self.assertLessEqual(np.linalg.norm(point-points[0]),.01+1e-7)
        before,normal=relocation.qualities(points[faces]);after=points.copy();after[0]=point
        q,new_normal=relocation.qualities(after[faces])
        self.assertGreater(q.min(),before.min())
        self.assertTrue(np.all(np.einsum('ij,ij->i',normal,new_normal)>0))

    def test_cancelled_neighbourhood_normal_is_refused(self):
        points=np.vstack([self.points,[[0,-.001,0]]])
        self.assertIsNone(relocation.proposal(points,np.array([[0,1,2],[0,1,3]]),0,.01))

    def test_invalid_radius_is_refused(self):
        for radius in [0,-.01,.051]:
            with self.assertRaises(AssertionError):relocation.proposal(self.points,self.faces,2,radius)

    def test_failed_optimizer_is_refused(self):
        with patch.object(relocation,'minimize',return_value=SimpleNamespace(success=False,x=np.zeros(3))):
            self.assertIsNone(relocation.proposal(self.points,self.faces,2,.01))

    def test_nonfinite_optimizer_proposal_is_refused(self):
        with patch.object(relocation,'minimize',return_value=SimpleNamespace(success=True,x=np.array([float('nan'),0.,0.]))):
            self.assertIsNone(relocation.proposal(self.points,self.faces,2,.01))


@unittest.skipUnless(AVAILABLE,'Requires NumPy and SciPy')
class GradedSizeTests(unittest.TestCase):
    def setUp(self):
        self.points=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        self.faces=np.array([[0,1,2],[0,3,1],[1,3,2],[0,2,3]])
        self.markers=np.array([4,1,2,3])

    def test_rotor_values_and_analytic_far_cap(self):
        sizes=graded.nodal_sizes(self.points,self.faces,self.markers,near=.1,far=.25,growth=.2)
        np.testing.assert_array_equal(sizes,[.1,.1,.1,.25])

    def test_translation_and_unit_conversion_preserve_the_field(self):
        sizes=graded.nodal_sizes(self.points,self.faces,self.markers,near=.1,far=.5,growth=.2)
        shifted=graded.nodal_sizes(self.points*1000+[20,-30,40],self.faces,self.markers,near=100,far=500,growth=.2)
        np.testing.assert_allclose(shifted,sizes*1000,rtol=0,atol=1e-12)

    def test_missing_rotor_and_nonfinite_input_are_refused(self):
        with self.assertRaises(ValueError):graded.nodal_sizes(self.points,self.faces,np.ones(4))
        points=self.points.copy();points[0,0]=float('nan')
        with self.assertRaises(ValueError):graded.nodal_sizes(points,self.faces,self.markers)


class RelocationCheckpointTests(unittest.TestCase):
    def test_executed_source_bytes_are_preserved(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/local-relocation-20261022.json').read_text())
        for name,expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)

    def test_certified_surface_does_not_admit_the_refused_adaptive_volume(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/local-relocation-20261022.json').read_text())
        surface=record['surface'];self.assertEqual(surface['poor_facet_progression'],[189,46,7,0]);self.assertGreaterEqual(surface['minimum_quality'],.05)
        self.assertTrue(surface['complete_original_and_reference_bounds_passed'])
        certificates=[step['certificate'] for step in surface['complete_certificates'] if 'certificate' in step]
        self.assertEqual(len(certificates),2)
        self.assertTrue(all(c['complete_containment_pass'] and c['envelope_bound_native_units']==.0225 for c in certificates))
        experiment=record['graded_tetrahedral_experiment'];self.assertTrue(experiment['point_budget_exhausted']);self.assertEqual(experiment['tetrahedra'],3995994)
        self.assertFalse(experiment['complete_changed_wall_certificate']);self.assertFalse(experiment['independent_exact_volume_audit_complete'])
        quality=record['native_quality_diagnostic'];self.assertEqual(quality['failed_quality_checks'],5);self.assertFalse(quality['full_quality_passed']);self.assertFalse(quality['CFD_executed'])
        for key in ['full_system_goal_complete','scale_verified','current_geometry_CFD_accepted','manufacturing_authorized','physical_validation']:
            self.assertFalse(record['scope'][key])


if __name__=='__main__':unittest.main()
