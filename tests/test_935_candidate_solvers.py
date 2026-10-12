import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    import trimesh
    from build_candidate_twin import properties, rotational_scenarios
    from prepare_candidate_cfd import prepare
    from stl_moments import moments, remove_declared_voxel_specks
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CandidateSolverTests(unittest.TestCase):
    def setUp(self):
        if not AVAILABLE and self._testMethodName not in (
            'test_mesh_quality_failure_prevents_solver', 'test_fea_runner_serial_settings_hash_and_new_directory'):
            self.skipTest('Requires working numpy/scipy/trimesh numerical runtime')

    def test_mass_inertia_and_parallel_axis_in_si(self):
        mesh = trimesh.creation.box(extents=[10,20,30]); mesh.apply_translation([5,0,0])
        result = properties(mesh,1000)
        self.assertAlmostEqual(result['mass_kg'],.006)
        expected = .006 * np.array([.02**2+.03**2, .01**2+.03**2, .01**2+.02**2]) / 12
        np.testing.assert_allclose(np.diag(result['inertia_about_COM_kg_m2']),expected)
        self.assertAlmostEqual(result['polar_inertia_about_candidate_z_kg_m2'],expected[2]+.006*.005**2)

    def test_streamed_binary_moments_match_independent_mesh_and_reject_truncation(self):
        mesh=trimesh.creation.box(extents=[10,20,30]);mesh.apply_translation([5,-7,11])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'box.stl';mesh.export(path);result=moments(path)
            expected=mesh.mass_properties
            origin=expected['inertia']+mesh.volume*(np.eye(3)*(mesh.center_mass@mesh.center_mass)-np.outer(mesh.center_mass,mesh.center_mass))
            self.assertAlmostEqual(result['conditional_volume_mm3'],6000)
            np.testing.assert_allclose(result['centroid_mm'],mesh.center_mass)
            np.testing.assert_allclose(result['volume_inertia_about_origin_mm5'],origin)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaises(ValueError):moments(path)

    def test_declared_speck_removal_preserves_main_body_and_refuses_ambiguity(self):
        body=trimesh.creation.box(extents=[10,20,30])
        speck=trimesh.creation.box(extents=[.2,.2,.2]);speck.apply_translation([40,0,0])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.stl';trimesh.util.concatenate([body,speck]).export(source)
            region={'classification':'generated_voxel_speck','triangles':12,'bounds_mm':speck.bounds.tolist()}
            report=remove_declared_voxel_specks(source,root/'clean.stl',[region])
            self.assertEqual(report['triangles_removed_per_region'],[12])
            self.assertAlmostEqual(moments(root/'clean.stl')['conditional_volume_mm3'],6000)
            with self.assertRaises(ValueError):remove_declared_voxel_specks(source,root/'bad.stl',[{**region,'triangles':24}])
            with self.assertRaises(FileExistsError):remove_declared_voxel_specks(source,root/'clean.stl',[region])

    def test_open_mesh_and_invalid_density_rejected(self):
        mesh = trimesh.creation.box(); mesh.update_faces(np.arange(len(mesh.faces)-1))
        with self.assertRaises(ValueError): properties(mesh,1000)
        for value in (0,float('nan'),True):
            with self.assertRaises(ValueError): properties(trimesh.creation.box(),value)

    def test_constant_braking_work_equals_kinetic_energy(self):
        values=properties(trimesh.creation.box(extents=[10,20,30]),1000)
        for row in rotational_scenarios(values):
            omega=row['rotor_rpm_assumed']*np.pi/30
            work=row['deceleration_torque_nm']*row['stop_time_s_assumed']*omega/2
            self.assertAlmostEqual(work,-row['kinetic_energy_j'])

    def test_cfd_stl_is_explicitly_si_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'rotor.stl'
            original = trimesh.creation.box(extents=[10,20,30]); original.export(source)
            case = {'purpose':'hypothesis_screen','assumptions':[{'rejection_test':'Bench'}], 'cfd':{
                'rotor_stl_path':str(source),'rotor_stl_sha256':sha(source),
                'duct_half_width_m':.18,'duct_half_height_m':.12,'flow_m3_s':.6,
                'rotor_rpm':6000,'air_density_kg_m3':1.15,'kinematic_viscosity_m2_s':1.55e-5,
                'rotating_zone_radius_m':.16,'rotating_zone_z_m':[-.075,.075],
                'turbulence_intensity':.03,'turbulence_length_m':.007,'iterations':20,
                'mesh_cells':{'coarse':[20,20,16],'medium':[28,28,22],'fine':[36,36,28]}}}
            path=root/'case.json';path.write_text(json.dumps(case));out=prepare(path,root/'output')
            for name in case['cfd']['mesh_cells']:
                mesh=trimesh.load_mesh(out/name/'constant/triSurface/rotor.stl')
                np.testing.assert_allclose(mesh.bounds,original.bounds*.001,rtol=1e-6)
                self.assertNotIn('scale 0.001', (out/name/'system/snappyHexMeshDict').read_text())
                self.assertIn('kOmegaSST',(out/name/'constant/turbulenceProperties').read_text())
            self.assertEqual(sha(source),case['cfd']['rotor_stl_sha256'])
            with self.assertRaises(ValueError):prepare(path,root/'output')
            case['cfd']['rotor_stl_sha256']='0'*64;path.write_text(json.dumps(case))
            with self.assertRaises(ValueError):prepare(path,root/'wrong-hash')

    def test_mesh_quality_failure_prevents_solver(self):
        if not shutil.which('bash'):
            self.skipTest('Bash unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);binary=root/'bin';binary.mkdir()
            for name in ('surfaceCheck','blockMesh','snappyHexMesh','checkMesh','topoSet','simpleFoam'):
                tool=binary/name
                tool.write_text('#!/bin/sh\n'+('echo "Failed mesh checks"\n' if name=='checkMesh' else
                    'touch solver-was-called\n' if name=='simpleFoam' else 'exit 0\n'))
                tool.chmod(0o700)
            import os
            env={**os.environ,'WM_PROJECT_VERSION':'v2406','PATH':str(binary)+os.pathsep+os.environ['PATH']}
            result=subprocess.run(['bash',str(SOURCE/'run_candidate_cfd.sh'),str(root)],env=env,capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse((root/'solver-was-called').exists())
            self.assertEqual((root/'solver.exit').read_text().strip(),'2')

    def test_fea_runner_serial_settings_hash_and_new_directory(self):
        if not shutil.which('sha256sum'):
            self.skipTest('Linux worker hash utility unavailable')
        import os
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);binary=root/'bin';binary.mkdir();solver=binary/'ccx'
            solver.write_text('#!/bin/sh\ntest "$OMP_NUM_THREADS" = 1 || exit 9\ntest "$CCX_NPROC_RESULTS" = 1 || exit 9\nprintf "Job finished\\n"\n')
            solver.chmod(0o700);deck=root/'deck.inp';deck.write_text('*HEADING\nFixture\n')
            env={**os.environ,'PATH':str(binary)+os.pathsep+os.environ['PATH']}
            command=['bash',str(SOURCE/'run_candidate_fea.sh'),str(deck),sha(deck),str(root/'solve')]
            result=subprocess.run(command,env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((root/'solve/ccx.exit').read_text().strip(),'0')
            self.assertNotEqual(subprocess.run(command,env=env,capture_output=True).returncode,0)
            command[-2]='0'*64;command[-1]=str(root/'wrong-hash')
            self.assertNotEqual(subprocess.run(command,env=env,capture_output=True).returncode,0)
            self.assertFalse((root/'wrong-hash').exists())

    def test_hexahedron_jacobians_units_and_connectivity_guard(self):
        try:
            from prepare_candidate_fea import prepare as prepare_fea
        except (ImportError, OSError):
            self.skipTest('Optional native Gmsh runtime unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);grid=root/'grid.json'
            cells=[[i,j,k] for i in range(-2,2) for j in range(-2,2) for k in range(2)
                   if not (i in (-1,0) and j in (-1,0))]
            payload={'schema':'935-signed-distance-hexa-grid-v1','input_sha256':'0'*64,
                     'pitch_mm':1,'cells':cells}
            grid.write_text(json.dumps(payload))
            case={'purpose':'hypothesis_screen','scale_verified':False,'grid_path':str(grid),
                  'grid_sha256':sha(grid),'rotor_stl_sha256':'0'*64,'bore_radius_mm':.1,
                  'bore_selection_tolerance_mm':2,'rotor_rpm':6000,'material_id':'alsi10mg',
                  'maximum_elements':100,'expected_volume_mm3':len(cells),
                  'maximum_volume_relative_error':.01}
            path=root/'case.json';path.write_text(json.dumps(case));out=prepare_fea(path,root/'out')
            receipt=json.loads((out/'receipt.json').read_text())
            self.assertAlmostEqual(receipt['minimum_scaled_Jacobian'],1)
            self.assertEqual(receipt['C3D8_elements'],len(cells))
            self.assertEqual(receipt['CAD_volume_relative_error'],0)
            deck=(out/'rotor.inp').read_text()
            self.assertIn('*ELEMENT,TYPE=C3D8',deck)
            self.assertIn('70000,0.33',deck)
            self.assertIn('2.67e-09',deck)
            payload['cells'].append([20,20,20]);grid.write_text(json.dumps(payload))
            case['grid_sha256']=sha(grid);path.write_text(json.dumps(case))
            with self.assertRaisesRegex(ValueError,'disconnected'):prepare_fea(path,root/'disconnected')

    def test_usd_rotated_non_degenerate_inertia(self):
        try:
            from pxr import Usd
        except ImportError:
            self.skipTest('Optional USD authoring runtime unavailable')
        from build_candidate_twin import build
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'rotor.stl'
            mesh=trimesh.creation.box(extents=[10,20,30])
            mesh.apply_transform(trimesh.transformations.rotation_matrix(.61,[1,2,3]))
            mesh.export(source)
            case={'purpose':'hypothesis_screen','scale_verified':False,'rotor_stl_path':str(source),
                  'rotor_stl_sha256':sha(source),'rotor_rpm':6000}
            path=root/'case.json';path.write_text(json.dumps(case));out=build(path,root/'usd')
            self.assertTrue(json.loads((out/'receipt.json').read_text())['USD_reread_passed'])
            self.assertFalse(json.loads((out/'receipt.json').read_text())['dynamic_simulation_executed'])


if __name__ == '__main__':unittest.main()
