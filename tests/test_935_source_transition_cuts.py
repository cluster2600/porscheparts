"""Synthetic adversarial proofs for original-triangle transition partitions."""
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
import tempfile

import numpy as np


SOURCE = Path(__file__).resolve().parents[1]/'docs/research/935-source-transition-cuts-20261106/source'


def load(name):
    spec = importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = load('build_transition_cuts')
checker = load('check_transition_cuts')
assembly = load('assemble_source_reference')


def fixture():
    vertices = np.array([[0.,0.,2.],[2.,0.,-1.],[0.,2.,-1.],[-2.,-2.,-1.]])
    faces = np.array([[0,1,2],[0,2,3],[0,3,1],[1,3,2]])
    plane = producer.rational([0.,0.,1.,0.])
    exact = [producer.rational(p) for p in vertices]
    exact += [producer.intersection(exact[0],exact[i],plane) for i in (1,2,3)]
    edge_nodes = {(0,1):4,(0,2):5,(0,3):6}
    triangles = [];parents = [];sides = []
    for parent,face in enumerate(faces[:3]):
        tri = list(map(int,face))
        for side in (-1,1):
            half = producer.clip(tri,{0:1,1:-1,2:-1,3:-1},edge_nodes,side)
            triangles.extend(half);parents.extend([parent]*len(half));sides.extend([side]*len(half))
    data = dict(points=np.array([list(map(float,p)) for p in exact]),triangles=np.array(triangles),
                source_vertex_ids=np.array([0,1,2,3,-1,-1,-1]),
                source_edge_codes=np.array([-1,-1,-1,-1,1,2,3]),
                node_plane_indices=np.array([-1,-1,-1,-1,0,0,0]),
                parent_source_face_ids=np.array(parents),triangle_halfspaces=np.array(sides),
                triangle_regions=np.ones(len(triangles),dtype=int))
    rows = [dict(region=1,plane=0)]
    region_data = {1:dict(transition_source_face_ids=np.arange(3),section_edge_codes=np.array([1,2,3]))}
    return vertices,faces,[plane],rows,region_data,data


class TransitionCuts(unittest.TestCase):
    def test_public_receipt_binds_executed_sources_and_preserves_open_goal(self):
        report = json.loads((SOURCE.parent/'results.json').read_text())
        hashes = {}
        for item in report['executed_sources']:
            with (SOURCE/item['name']).open('rb') as stream:
                digest = hashlib.file_digest(stream,'sha256').hexdigest()
            self.assertEqual(digest,item['sha256']);hashes[item['name']] = digest
        self.assertEqual(report['independent_source_proof']['source_sha256'],hashes['check_transition_cuts.py'])
        self.assertEqual(report['source_construction']['private_fragments_sha256'],
                         report['independent_source_proof']['fragments_sha256'])
        references = report['complete_reference_assembly']['references']
        self.assertEqual(sum(row['actual_OBJ_triangles'] for row in references),2465836+2*726)
        self.assertEqual(sum(row['clipped_transition_fragments'] for row in references),3*726)
        self.assertTrue(report['complete_reference_assembly']['reconciliation']['exact_edge_and_boundary_reconciliation'])
        for stage in ('first_native_readback','actual_saved_native_readback'):
            native = report[stage]
            self.assertEqual(sum(row['derived_triangles'] for row in native['regions']),2178)
            self.assertTrue(native['controls']['moved_acquired_vertex_below_constructed_guard_refused'])
            self.assertTrue(native['controls']['unsewn_same_facets_refused'])
            self.assertTrue(all(row['comparison']['original_vertex_roundtrip_maximum_nominal_mm']==0 for row in native['regions']))
        self.assertTrue(report['actual_native_registration']['all_726_actual_saved_section_nodes_registered'])
        self.assertTrue(all(row['comparisons']['inside_to_outside_maximum_nominal_mm']==0
                            for row in report['actual_native_registration']['regions']))
        for field in ('caps_or_hidden_surfaces_added','unresolved_original_holes_filled','complete_bare_head_created',
                      'anatomical_identity_accepted','physical_acceptance','manufacturing_authorized','print_ready','all_G0_to_G5'):
            self.assertFalse(report['release'][field])
        self.assertTrue(report['release']['full_goal_active'])
        self.assertNotIn('/Users/',json.dumps(report))

    def assembly_fixture(self, directory):
        vertices,faces,planes,rows,region_data,data = fixture()
        points = data['points'];mapping = np.arange(len(points))
        negative = np.flatnonzero(data['triangle_halfspaces']<0)
        target = Path(directory)/'retained'
        body = np.r_[faces[[3]],data['triangles'][negative]]
        assembly.write_reference(target,points,body,np.r_[3,data['parent_source_face_ids'][negative]],
                                 np.r_[-1,negative])
        section = np.array([4*7+5,4*7+6,5*7+6])
        arguments = (target,0,vertices,faces,np.array([-1,-1,-1,0]),data,mapping,points,{0:section})
        return arguments

    def test_whole_reference_OBJ_is_rejoined_to_originals_and_proved_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            result,_ = assembly.inspect_reference(*self.assembly_fixture(directory))
            self.assertEqual(result['original_whole_triangles'],1)
            self.assertEqual(result['clipped_transition_fragments'],6)
            self.assertEqual(result['boundary_edges'],3)
            self.assertTrue(result['actual_OBJ_readback_exact'])

    def test_modified_actual_OBJ_and_NPZ_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            values = self.assembly_fixture(directory);target = values[0]
            path = target.with_suffix('.obj');lines = path.read_text().splitlines()
            for i,line in enumerate(lines):
                if line.startswith('v '):
                    words = line.split();words[1] = str(float(words[1])+.01)
                    lines[i] = ' '.join(words);break
            path.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(AssertionError):assembly.inspect_reference(*values)
        with tempfile.TemporaryDirectory() as directory:
            values = self.assembly_fixture(directory);path = values[0].with_suffix('.npz')
            stored = assembly.arrays(path);stored['triangles'][1] = stored['triangles'][0]
            np.savez_compressed(path,**stored)
            with self.assertRaises(AssertionError):assembly.inspect_reference(*values)

    def test_literal_control_partitions(self):
        self.assertTrue(all(producer.controls().values()))
        self.assertTrue(all(checker.controls().values()))

    def test_exact_tetrahedron_partition_and_opposite_interfaces(self):
        result = checker.inspect(*fixture())
        self.assertEqual(result['original_transition_triangles'],3)
        self.assertEqual(result['derived_triangles'],9)
        self.assertTrue(result['each_original_triangle_exactly_tiled_by_two_opposite_halves'])
        self.assertTrue(result['opposite_halves_share_identical_nodes_and_reversed_section_edges'])

    def test_even_one_ulp_endpoint_substitution_is_rejected(self):
        values = fixture();data = values[-1]
        data['points'][4,0] = np.nextafter(data['points'][4,0],np.inf)
        with self.assertRaises(AssertionError):checker.inspect(*values)

    def test_wrong_original_edge_origin_is_rejected(self):
        values = fixture();values[-1]['source_edge_codes'][4] = 6
        with self.assertRaises(AssertionError):checker.inspect(*values)

    def test_duplicate_same_count_fragment_is_rejected(self):
        values = fixture();data = values[-1]
        data['triangles'][1] = data['triangles'][0]
        with self.assertRaises(AssertionError):checker.inspect(*values)

    def test_wrong_halfspace_and_parent_assignment_are_rejected(self):
        for field in ('triangle_halfspaces','parent_source_face_ids'):
            values = fixture();data = values[-1]
            data[field][0] = -data[field][0] if field=='triangle_halfspaces' else 1
            with self.assertRaises(AssertionError):checker.inspect(*values)


if __name__=='__main__':unittest.main()
