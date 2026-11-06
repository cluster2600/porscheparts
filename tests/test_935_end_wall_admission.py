"""Acquired-binormal, immutable ancestry and complete-cap provenance contracts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-end-wall-admission-20261106/source'


def module(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


admission=module('admit_end_walls')
inspection=module('verify_end_wall_admission')
assembly=module('assemble_end_wall_candidate')
LIMITS=dict(min_edges=3,max_edges=128,max_diagonal_nominal_mm=3.,max_plane_residual_nominal_mm=.25,
            min_distinct_acquired_owners=2,minimum_acquired_binormal_signed_p10=.8)


class EndWallAdmission(unittest.TestCase):
    def fixture(self):
        return np.array([[.2,0.,.1],[.2,.2,.1],[.2,.2,-.1],[.2,0.,-.1]]),np.array([[0.,0.,1.],[0.,0.,-1.]])

    def test_literal_independent_positive_and_reason_specific_controls(self):
        self.assertEqual(inspection.controls(LIMITS),16)

    def test_two_opposed_acquired_skins_support_positive_end_wall_binormals(self):
        points,normals=self.fixture()
        reasons,descriptors=admission.screen(points,np.array([0,2]),normals,[0,1],LIMITS,inspection.simple)
        self.assertFalse(reasons)
        self.assertEqual(descriptors['minimum_acquired_binormal_signed_dot'],1.)
        self.assertEqual(descriptors['acquired_binormal_signed_p10'],1.)
        self.assertTrue(np.array_equal(normals@np.array([1.,0.,0.]),[0.,0.]))

    def test_global_reversal_changes_material_side_verdict(self):
        points,normals=self.fixture()
        reasons,_=admission.screen(points[[0,3,2,1]],np.array([1,3]),-normals[::-1],[1,0],LIMITS,inspection.simple)
        self.assertIn('nonpositive_acquired_edge_binormal',reasons)

    def test_duplicate_or_inferred_only_owners_cannot_supply_acquired_evidence(self):
        points,normals=self.fixture()
        reasons,_=admission.screen(points,np.array([0,2]),normals,[0,0],LIMITS,inspection.simple)
        self.assertIn('insufficient_distinct_actual_acquired_owners',reasons)
        reasons,_=admission.screen(points,np.array([],dtype=int),np.empty((0,3)),[],LIMITS,inspection.simple)
        self.assertIn('insufficient_distinct_actual_acquired_owners',reasons)

    def test_cycle_identity_ignores_rotation_but_preserves_direction_and_raw_owner(self):
        signatures=np.array([[0,12,12,-1,-1,1,2],[7,9,4,8,-1,2,3],[0,14,14,-1,-1,3,4],[7,9,4,8,-1,4,1]])
        digest=admission.cycle_identity(signatures)
        for shift in range(4):self.assertEqual(admission.cycle_identity(np.roll(signatures,shift,axis=0)),digest)
        self.assertNotEqual(admission.cycle_identity(signatures[::-1]),digest)
        changed=signatures.copy();changed[0,1:3]=13
        self.assertNotEqual(admission.cycle_identity(changed),digest)

    def test_inferred_edge_ancestry_survives_local_vertex_remapping(self):
        vertices=np.array([[0.,0.,.1],[.2,0.,.1],[.2,0.,-.1],[0.,0.,-.1]])
        raw={'vertices':vertices};keys=np.array([[0,0,1],[1,2,3]])
        mesh=dict(points=vertices,triangles=np.array([[1,0,3]]),inferred_surface_kind=np.array([7]),original_face_ids=np.array([-1]))
        expected=admission.pair_ancestry(mesh,0,raw,keys,5,7,[0,3])
        order=np.array([3,1,0,2]);inverse=np.argsort(order)
        remapped=dict(mesh,points=vertices[order],triangles=inverse[mesh['triangles']])
        self.assertEqual(admission.pair_ancestry(remapped,0,raw,keys,5,7,inverse[[0,3]]),expected)

    def test_moved_inferred_corner_and_wrong_kind_fail_ancestry(self):
        vertices=np.array([[0.,0.,.1],[.2,0.,.1],[.2,0.,-.1],[0.,0.,-.1]])
        mesh=dict(points=vertices.copy(),triangles=np.array([[1,0,3]]),inferred_surface_kind=np.array([7]),original_face_ids=np.array([-1]))
        raw={'vertices':vertices};keys=np.array([[0,0,1],[1,2,3]])
        mesh['points'][3,1]=.01
        with self.assertRaises(AssertionError):admission.pair_ancestry(mesh,0,raw,keys,5,7,[0,3])
        mesh['points']=vertices.copy();mesh['inferred_surface_kind'][0]=6
        with self.assertRaises(AssertionError):admission.pair_ancestry(mesh,0,raw,keys,5,7,[0,3])

    def test_cap_namespace_is_new_and_every_older_channel_remains_exact(self):
        base=dict(points=np.zeros((4,3)),global_node_ids=np.arange(4),triangles=np.array([[0,1,2],[0,2,3]]),
                  inferred_surface_kind=np.array([0,7]),original_face_ids=np.array([20,-1]),source_patch_curve_ids=np.array([-1,60000017]),
                  source_strip_cap_curve_ids=np.array([17,-1]),source_opposed_wall_pair_ids=np.array([-1,17]))
        result=assembly.compose(base,{17:np.array([[1,0,3]])})
        for key,value in base.items():
            if key in ('points','global_node_ids'):self.assertTrue(np.array_equal(result[key],value))
            else:self.assertTrue(np.array_equal(result[key][:2],value))
        self.assertEqual(result['inferred_surface_kind'].tolist(),[0,7,8])
        self.assertEqual(result['source_end_wall_cap_curve_ids'].tolist(),[-1,-1,17])
        self.assertEqual(result['end_wall_cap_immediate_parent_face_rows'].tolist(),[0,1,-1])
        self.assertEqual(result['source_patch_curve_ids'][-1],70000017)
        self.assertEqual(result['source_opposed_wall_pair_ids'][-1],-1)

    def test_all_executed_sources_helpers_and_derivative_parents_are_bound(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['reused_helpers']:self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['derivative_source_ancestry']:self.assertEqual(hashlib.sha256((ROOT/row['parent_path']).read_bytes()).hexdigest(),row['parent_sha256'])
        self.assertNotIn('/Users/',json.dumps(result))

    def test_full_source_admission_is_not_physical_hole_or_manufacturing_approval(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        self.assertEqual(result['independent_admission']['new_wall_border_walks'],216)
        self.assertEqual(result['independent_admission']['admitted_trials'],18)
        self.assertFalse(result['goal_complete']);self.assertFalse(result['manufacturing_authorized'])
        self.assertFalse(result['final_audit']['closed_volume'])
        self.assertTrue(result['final_audit']['surface_study_checks_passed'])


if __name__=='__main__':
    unittest.main()
