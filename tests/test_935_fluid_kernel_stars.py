from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0,str(SOURCE))
try:
    import numpy as np
    import rebuild_fluid_edge_stars as kernel
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Requires NumPy and SciPy')
class FluidKernelTests(unittest.TestCase):
    def fixture(self):
        return np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]]),np.array([[0,1,2,3]])

    def test_analytic_incentre_and_translated_scale_controls(self):
        kernel.self_test()

    def test_outside_and_zero_volume_children_are_refused(self):
        vertices,cells=self.fixture()
        point,children,ids,local_cells=kernel.kernel_proposal(vertices,cells,vertices.mean(axis=0))
        self.assertTrue(kernel.positive_partition(vertices,cells,point,children,ids,local_cells))
        for invalid in [np.array([2.,2,2]),vertices[0]]:
            self.assertFalse(kernel.positive_partition(vertices,cells,invalid,children,ids,local_cells))

    def test_all_four_boundary_faces_and_original_points_are_retained(self):
        vertices,cells=self.fixture();before=vertices.copy()
        _,children,_,_=kernel.kernel_proposal(vertices,cells,vertices.mean(axis=0))
        np.testing.assert_array_equal(vertices,before)
        expected=np.array([[0,1,2],[0,1,3],[0,2,3],[1,2,3]])
        np.testing.assert_array_equal(kernel.base.outer_faces(children),expected)

    def test_nonmanifold_cavity_is_refused(self):
        _,cells=self.fixture()
        with self.assertRaises(ValueError):kernel.outer_oriented(np.vstack([cells,cells,cells]))

    def test_sample_limit_fails_before_input_read_or_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for limit in [0,5001]:
                output=root/f'output-{limit}'
                with self.assertRaises(ValueError):kernel.run(root/'absent-input',limit,output)
                self.assertFalse(output.exists())

    def test_export_retains_original_points_boundary_and_markers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepared=root/'prepared';parent=root/'parent';proposal=root/'proposal'
            for p in [prepared,parent,proposal]:p.mkdir()
            (prepared/'receipt.json').write_text('{}');(prepared/'fluid.smesh').write_text('synthetic formatting fixture\n')
            vertices,cells=self.fixture();boundary=np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]]);markers=np.arange(1,5)
            np.savez(parent/'volume.npz',vertices=vertices,tetrahedra=cells,boundary=boundary,markers=markers)
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            (parent/'assessment.json').write_text(json.dumps({'volume_npz_sha256':sha(parent/'volume.npz'),'prepared_receipt_sha256':sha(prepared/'receipt.json')}))
            added=np.vstack([vertices,[.25,.25,.25]]);new_cells=np.column_stack([np.full(4,4),boundary])
            command=[sys.executable,str(SOURCE/'export_fluid_kernel_candidate.py'),str(prepared),str(parent),str(proposal)]
            env=dict(os.environ,PYTHONPATH=str(SOURCE))
            for mutation in ['none','vertex','boundary','marker']:
                points=added.copy();faces=boundary.copy();tags=markers.copy()
                if mutation=='vertex':points[0,0]=.125
                if mutation=='boundary':faces[0,0]=4
                if mutation=='marker':tags[0]=2
                np.savez(proposal/'candidate.npz',vertices=points,tetrahedra=new_cells,boundary=faces,markers=tags)
                (proposal/'receipt.json').write_text(json.dumps({'candidate_sha256':sha(proposal/'candidate.npz'),'parent_assessment_sha256':sha(parent/'assessment.json')}))
                output=root/f'output-{mutation}'
                result=subprocess.run(command+[str(output)],env=env,capture_output=True,text=True)
                if mutation=='none':
                    self.assertEqual(result.returncode,0,result.stderr)
                    from import_conforming_volume import table
                    np.testing.assert_array_equal(table(output/'fluid.1.node','node'),added)
                    np.testing.assert_array_equal(table(output/'fluid.1.ele','ele'),new_cells)
                    self.assertEqual(json.loads((output/'execution.json').read_text())['added_interior_mesh_points'],1)
                else:
                    self.assertNotEqual(result.returncode,0)
                    self.assertFalse(output.exists())


class FluidKernelCheckpointTests(unittest.TestCase):
    def test_checkpoint_binds_sources_and_preserves_unqualified_scope(self):
        checkpoint=ROOT/'docs/research/935-horizontal-cooling/fluid-kernel-continuation-20261022.json'
        record=json.loads(checkpoint.read_text())
        for path,digest in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertTrue(all(value is False for value in record['scope'].values()))
        self.assertFalse(record['PicoGK_design_master_changed'])
        self.assertEqual(record['new_rotor_PDE_runs'],0)
        self.assertEqual(record['accepted_interior_stars'],1537)
        self.assertEqual([v['small_determinant_cells'] for v in record['native_cases'].values()],[2090,2005,840,576,525,519])
        for case in record['native_cases'].values():
            self.assertTrue(case['all_cell_orientations_positive'])
            self.assertTrue(case['exact_volume_equal_to_PLC'])
            self.assertTrue(case['complete_boundary_coordinate_triangle_marker_bijection'])
            self.assertTrue(case['original_quality_dictionary_unchanged'])
            self.assertFalse(case['extended_mesh_quality_passed'])
            self.assertEqual(case['failed_native_checks'],4)
        proof=record['prefix_and_boundary_verification']
        self.assertTrue(proof['all_original_vertices_retained_as_exact_prefix'])
        self.assertTrue(proof['boundary_triangles_and_markers_exactly_equal'])
        self.assertEqual(proof['added_interior_air_mesh_points'],1537)
        self.assertEqual(record['sweeps']['5']['eligible_internal_edges'],394)
        self.assertEqual(record['sweeps']['5']['sampled_edges'],394)
        self.assertEqual(record['sweeps']['5']['decisions'].get('accepted_disjoint_star',0),0)
        self.assertFalse(record['global_mesh_optimization_converged'])
        self.assertFalse(record['runtime']['new_paid_instance_created'])
        self.assertTrue(record['private_archive']['all_members_verified'])
        self.assertTrue(record['private_archive']['Mac_all_members_verified'])
        self.assertEqual(record['private_archive']['entries'],203)


if __name__=='__main__':unittest.main()
