"""Synthetic source-origin and surface-fan adversaries for retained boundary review."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1]/'docs/research/935-retained-boundaries-20261106/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


producer = module('audit_retained_boundaries')
checker = module('check_retained_boundaries')


def contact_fixture():
    points = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]])
    faces = np.array([[0,1,2],[0,3,4]])
    p = producer.fans_and_cycles(faces,len(points));rows = [];centres = [];normals = []
    atlas = np.array([0,1]);parents = np.arange(2)
    for i,(a,b) in enumerate(zip(p['offsets'][:-1],p['offsets'][1:])):
        ids = p['cycle_edges'][a:b];edges = p['boundary'][ids]
        stats,centre,normal = producer.geometry(points[edges[:,0]])
        centres.append(centre);normals.append(normal)
        rows.append(dict(curve=i,edges=len(ids),**stats,repeated_original_node_visits=0,
                         original_atlas_chart_indices=atlas[parents[p['owners'][ids]]].tolist(),
                         closure_authorized=False,physical_classification='unreviewed'))
        rows[-1]['original_atlas_chart_indices'] = sorted(set(rows[-1]['original_atlas_chart_indices']))
    data = dict(boundary_global_nodes=p['boundary'],boundary_face_rows=p['owners'],
                from_fan_labels=p['from_fans'],to_fan_labels=p['to_fans'],
                cycle_offsets=p['offsets'],cycle_boundary_edge_ids=p['cycle_edges'],
                fitted_centres=np.array(centres),fitted_normals=np.array(normals))
    return data,faces,rows,points,len(points),atlas,parents


class RetainedBoundaryOrigins(unittest.TestCase):
    def test_public_receipt_binds_all_sources_and_complete_saved_boundary_set(self):
        report = json.loads((SOURCE.parent/'results.json').read_text())
        for row in report['executed_sources']:
            with (SOURCE/row['name']).open('rb') as stream:
                self.assertEqual(hashlib.file_digest(stream,'sha256').hexdigest(),row['sha256'])
        source = report['source_audit'];check = report['independent_source_check']
        self.assertEqual(source['retained_boundary_edges'],sum(source['edge_origin_counts'].values()))
        self.assertEqual(source['edge_origin_counts'],check['independently_rejoined_retained_edge_origins'])
        self.assertEqual(source['retained_boundary_curves'],report['curve_summary']['total_curves'])
        for key in ('first_native_source_readback','actual_saved_native_source_readback'):
            native = report[key]
            self.assertEqual(native['verified_curve_objects'],source['retained_boundary_curves'])
            self.assertEqual(native['native_edges'],source['retained_boundary_edges'])
            self.assertEqual(native['native_faces'],0);self.assertEqual(native['native_solids'],0)
            self.assertEqual(native['maximum_original_coordinate_error_nominal_mm'],0)
            self.assertTrue(native['all_directed_source_segments_once'])
            self.assertTrue(native['controls']['reversed_source_walk_refused'])
            self.assertTrue(native['controls']['moved_original_below_constructed_guard_refused'])
        self.assertEqual(report['native_review_document']['object_count'],source['retained_boundary_curves'])
        self.assertTrue(report['native_review_document']['all_physical_roles_unreviewed'])
        for field in ('source_geometry_modified','any_curve_filled','complete_bare_head_created',
                      'physical_acceptance','manufacturing_authorized','print_ready','all_G0_to_G5'):
            self.assertFalse(report['release'][field])
        self.assertEqual(report['release']['physical_classifications_accepted'],0)
        self.assertTrue(report['release']['full_goal_active'])
        self.assertNotIn('/Users/',json.dumps(report))

    def test_literal_origin_and_contact_controls(self):
        self.assertTrue(all(producer.controls().values()))

    def test_point_contact_is_two_surface_boundary_cycles(self):
        values = contact_fixture();data = values[0]
        boundary,_,start,end = checker.inspect_cycles(*values)
        self.assertEqual(len(boundary),6)
        self.assertEqual(len(data['cycle_offsets'])-1,2)
        self.assertEqual(len(set(start[data['boundary_global_nodes'][:,0]==0])),2)

    def test_fan_merge_and_incomplete_edge_inventory_are_rejected(self):
        values = contact_fixture();data = values[0]
        labels = data['from_fan_labels'][data['boundary_global_nodes'][:,0]==0]
        for key in ('from_fan_labels','to_fan_labels'):
            data[key][data[key]==labels[1]] = labels[0]
        with self.assertRaisesRegex(AssertionError,'vertex-fan partition'):checker.inspect_cycles(*values)
        values = contact_fixture();values[0]['boundary_global_nodes'] = values[0]['boundary_global_nodes'][:-1]
        with self.assertRaisesRegex(AssertionError,'boundary edge inventory'):checker.inspect_cycles(*values)

    def test_same_edges_joined_through_contact_are_rejected(self):
        values = contact_fixture();data,faces,rows,points,vcount,atlas,parents = values
        data['cycle_offsets'] = np.array([0,6]);rows = [dict(curve=0,edges=6)]
        with self.assertRaisesRegex(AssertionError,'jumps between surface fans'):
            checker.inspect_cycles(data,faces,rows,points,vcount,atlas,parents)

    def test_forged_closure_authority_is_rejected(self):
        values = contact_fixture();values[2][0]['closure_authorized'] = True
        with self.assertRaises(AssertionError):checker.inspect_cycles(*values)

    def test_quarantine_is_not_mislabeled_as_original_gap(self):
        faces = np.array([[0,1,2],[0,2,3]])
        edges = np.array([[0,1],[1,2],[2,0]]);owners = np.zeros(3,dtype=int);parents = np.array([0]);roles = np.array([0,-2])
        kind,curve,declared,_ = producer.attribute(edges,owners,parents,faces,roles,4,4,{})
        data = dict(edge_origin_kind=kind,raw_original_curve_ids=curve,declared_cut_regions=declared)
        result = checker.inspect_origins(faces,roles,parents,edges,owners,data,4,{},4)
        self.assertEqual(result['independently_rejoined_retained_edge_origins'],{1:2,2:1})
        data['edge_origin_kind'] = np.ones(3,dtype=np.int8)
        with self.assertRaises(AssertionError):checker.inspect_origins(faces,roles,parents,edges,owners,data,4,{},4)

    def test_unexplained_source_loss_is_rejected_independently(self):
        faces = np.array([[0,1,2],[0,2,3]]);edges = np.array([[0,1],[1,2],[2,0]])
        data = dict(edge_origin_kind=np.array([1,1,2]),raw_original_curve_ids=np.array([0,0,-1]),declared_cut_regions=np.zeros(3,dtype=int))
        with self.assertRaisesRegex(AssertionError,'Unexplained acquired surface loss'):
            checker.inspect_origins(faces,np.array([0,0]),np.array([0]),edges,np.zeros(3,dtype=int),data,4,{},4)

    def test_collinear_contour_does_not_define_a_plane(self):
        record,_,_ = producer.geometry(np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]]))
        self.assertEqual(record['affine_rank'],1)
        self.assertIsNone(record['plane_maximum_residual_nominal_mm'])


if __name__=='__main__':unittest.main()
