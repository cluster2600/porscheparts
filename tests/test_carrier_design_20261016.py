"""Keep thicker-shell trials inside the frozen carrier study interfaces."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

try:
    import numpy
except ImportError:
    numpy = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016'
BASELINE = SOURCE.parent / 'bionic-20261011/correction-20261013/selected-study.json'


class CarrierDesignTests(unittest.TestCase):
    def test_wall_bound_uses_positive_derivative_weights_and_conservative_slope(self):
        proof = json.loads((SOURCE / 'bounded-webs-wall-proof.json').read_text())
        x, y = proof['control_points_X'], proof['control_points_Y']
        dx = [b-a for a,b in zip(x,x[1:])]
        dy = [b-a for a,b in zip(y,y[1:])]
        self.assertTrue(all(value > 0 for value in dx))
        slope = max(abs(a/b) for a,b in zip(dy,dx))
        self.assertEqual(slope, 2/15)
        self.assertEqual(proof['maximum_abs_slope_bound'], slope)
        bound = proof['frozen_web_Y_translation_mm']/math.sqrt(1+slope*slope)
        self.assertEqual(proof['minimum_normal_distance_bound_mm'], bound)
        self.assertGreater(bound, proof['screen_mm'])

    def test_mass_sensitivities_preserve_every_other_geometry_and_load_parameter(self):
        plan = json.loads((SOURCE / 'plan.json').read_text())
        self.assertEqual(hashlib.sha256(BASELINE.read_bytes()).hexdigest(), plan['baseline_parameters_sha256'])
        baseline = json.loads(BASELINE.read_text())
        for trial in plan['mass_sensitivities']:
            settings = json.loads((SOURCE / (trial['id'] + '.json')).read_text())
            geometry = settings['geometry']
            self.assertEqual(geometry['arm_shell']['cap_mm'], 1.5)
            self.assertEqual(geometry['arm_shell']['web_mm'], 1.5)
            self.assertEqual(geometry['central_back_ribs']['width_mm'], trial['back_rib_width_mm'])
            self.assertGreaterEqual(trial['back_rib_width_mm'], 1.5)
            geometry['arm_shell']['cap_mm'] = baseline['geometry']['arm_shell']['cap_mm']
            geometry['arm_shell']['web_mm'] = baseline['geometry']['arm_shell']['web_mm']
            geometry['central_back_ribs']['width_mm'] = baseline['geometry']['central_back_ribs']['width_mm']
            self.assertEqual(geometry, baseline['geometry'])
            for name in ('material', 'load_cases', 'design_constraints'):
                self.assertEqual(settings[name], baseline[name])
        self.assertEqual(plan['criteria']['nominal_mass_kg_max'], 1.2)
        self.assertEqual(plan['criteria']['STEP_readback_relative_volume_error_max'], 1e-8)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_quadratic_tetrahedron_reproduces_affine_deformation_and_rejects_inversion(self):
        spec=importlib.util.spec_from_file_location('carrier_finite_work',SOURCE/'audit_finite_work.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        corners=numpy.array([[0.,0,0],[2,0,0],[0,3,0],[0,0,4]])
        points=numpy.vstack((corners,(corners[module.EDGE_PAIRS[:,0]]+corners[module.EDGE_PAIRS[:,1]])/2))
        gradient,weights=module.gradients(points[None])
        deformation=numpy.array([[1.1,.08,-.03],[-.01,.95,.02],[.04,.01,1.03]])
        u=points@(deformation-numpy.eye(3)).T+[4,3,2]
        actual=numpy.eye(3)+numpy.einsum('eni,eqnj->eqij',u[None],gradient)
        numpy.testing.assert_allclose(actual,numpy.broadcast_to(deformation,actual.shape),rtol=0,atol=2e-14)
        self.assertAlmostEqual(float(weights.sum()*4),4.)
        reflected=points.copy();reflected[:,0]*=-1
        with self.assertRaises(AssertionError):module.gradients(reflected[None])

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_plastic_work_integral_matches_exact_linear_hardening(self):
        spec=importlib.util.spec_from_file_location('carrier_hardening_work',SOURCE/'audit_finite_work.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        curve=numpy.array([[900.,0.],[1000.,.1]])
        strain=numpy.array([0.,.02,.08,.1])
        numpy.testing.assert_allclose(module.hardening_integral(strain,curve),900*strain+500*strain*strain,rtol=0,atol=2e-14)
        with self.assertRaises(AssertionError):module.hardening_integral(numpy.array([.101]),curve)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_first_piola_preserves_spatial_stress_power(self):
        spec=importlib.util.spec_from_file_location('carrier_piola',SOURCE/'audit_finite_work.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        f=numpy.array([[1.1,.08,-.03],[-.01,.95,.02],[.04,.01,1.03]])
        df=numpy.array([[.02,.01,-.03],[.04,-.01,.02],[-.03,.02,.05]])
        tensor=numpy.array([120.,90,60,12,5,-7])
        stress=numpy.array([[120.,12,5],[12,90,-7],[5,-7,60]])
        piola,jacobian=module.first_piola(tensor,f)
        self.assertAlmostEqual(float(numpy.sum(piola*df)),float(jacobian*numpy.sum(stress*(df@numpy.linalg.inv(f)))),places=12)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_finite_work_load_unload_cycle_has_exact_spring_work_and_zero_net_work(self):
        spec=importlib.util.spec_from_file_location('carrier_cycle_work',SOURCE/'audit_finite_work.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        corners=numpy.eye(4,3,k=-1)
        points=numpy.vstack((corners,(corners[module.EDGE_PAIRS[:,0]]+corners[module.EDGE_PAIRS[:,1]])/2))
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);name='rigid-translation'
            mesh='*NODE\n'+''.join(f'{i+1},{p[0]},{p[1]},{p[2]}\n' for i,p in enumerate(points))
            mesh+='*ELEMENT,TYPE=C3D10,ELSET=BODY\n1,'+','.join(map(str,range(1,11)))+'\n'
            (folder/'mesh.inp').write_text(mesh)
            # A rigid translation gives F=I and zero solid work. Each node's
            # external force balances its own unit spring, throughout the cycle.
            deck='*ELEMENT,TYPE=SPRING1,ELSET=EYES\n'+''.join(f'{100+i},{i}\n' for i in range(1,11))
            deck+='*SPRING,ELSET=EYES\n1\n1\n*CLOAD\n'+''.join(f'{i},1,1\n' for i in range(1,11))
            deck+='*CLOAD,OP=NEW\n'+''.join(f'{i},1,0\n' for i in range(1,11))
            (folder/(name+'.inp')).write_text(deck)
            plan={'unload_to_zero':True,'geometry_STEP_sha256':'synthetic'}
            (folder/'plan.json').write_text(json.dumps(plan))
            (folder/'mesh.json').write_text(json.dumps({'STEP_sha256':'synthetic'}))
            (folder/'runtime.json').write_text(json.dumps({'name':name,'mesh_sha256':module.sha(folder/'mesh.inp'),
                'input_sha256':module.sha(folder/(name+'.inp')),'constitutive_model':{'geometric_nonlinearity':True,'true_VM_yield_MPa':900}}))
            data=''
            for time,u in ((.5,.5),(1.,1.),(1.5,.5),(2.,0.)):
                data+=f' displacements (vx,vy,vz) for set ALLN and time {time}\n'
                data+=''.join(f'{i} {u} 0 0\n' for i in range(1,11))
                data+=f' stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY and time {time}\n'
                data+=''.join(f'1 {i} 0 0 0 0 0 0\n' for i in range(1,5))
                data+=f' equivalent plastic strain (elem, integ.pnt.,pe)for set BODY and time {time}\n'
                data+=''.join(f'1 {i} 0\n' for i in range(1,5))
            (folder/(name+'.dat')).write_text(data)
            result=module.audit(folder,folder/'result.json')
        self.assertTrue(result['all_frames_pass'])
        self.assertEqual([frame['load_factor'] for frame in result['frames']],[.5,1.,.5,0.])
        self.assertEqual(result['frames'][-1]['external_cumulative_work_Nmm'],0.)
        self.assertEqual(result['frames'][-1]['gross_external_cumulative_work_Nmm'],10.)
        self.assertEqual(result['frames'][-1]['internal_cumulative_work_Nmm'],0.)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_ccx_internal_curve_limit_explains_published_coupon_without_relaxing_tolerance(self):
        spec=importlib.util.spec_from_file_location('carrier_ccx_curve',SOURCE/'ccx_curve_reference.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        raw=numpy.loadtxt(SOURCE.parent/'process-20261016/material-luo-set1/flat-set-1-plastic.inp',delimiter=',',comments='*')
        effective=module.effective_curve(raw)
        self.assertEqual(raw.shape,(248,2));self.assertEqual(effective.shape,(200,2))
        self.assertAlmostEqual(effective[-1,1],raw[-1,1]-1e-10,places=15)
        expected=numpy.interp(.02,effective[:,1]+effective[:,0]/106000,effective[:,0])
        self.assertAlmostEqual(float(expected),1010.1836191878247,places=8)
        self.assertLess(abs(expected-1010.184),.01)
        bound,location=module.maximum_interpolation_difference(raw,effective)
        self.assertAlmostEqual(bound,.7249539949640393,places=8)
        self.assertGreater(location,0)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_eye_spring_rotation_matrix_matches_cross_product_and_known_ring(self):
        spec = importlib.util.spec_from_file_location('carrier_load_path', SOURCE / 'audit_load_path.py')
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        radius=6.75
        points=numpy.array([[radius,0,0],[-radius,0,0],[0,0,radius],[0,0,-radius]])
        matrix=module.rigid_matrix(points)
        mode=numpy.array([1,2,3,.1,.2,.3])
        numpy.testing.assert_allclose(numpy.einsum('nij,j->ni',matrix,mode),mode[:3]+numpy.cross(mode[3:],points))
        stiffness=250*numpy.einsum('nai,naj->ij',matrix,matrix)
        numpy.testing.assert_allclose(stiffness[:3,:3],1000*numpy.eye(3))
        self.assertEqual(stiffness[4,4],1000*radius*radius)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_plastic_parser_keeps_increment_and_integration_point_identity(self):
        spec = importlib.util.spec_from_file_location('carrier_plastic_analysis', SOURCE / 'analyze_plastic900.py')
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'coupon.dat'
            path.write_text(''' displacements (vx,vy,vz) for set ALLN and time 0.5
1 0 0 0
2 0.01 0 0
 stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY and time 0.5
1 1 900 0 0 0 0 0
 equivalent plastic strain (elem, integ.pnt.,pe)for set BODY and time 0.5
1 1 0.001
 displacements (vx,vy,vz) for set ALLN and time 1.0
1 0 0 0
2 0.02 0 0
 equivalent plastic strain (elem, integ.pnt.,pe)for set BODY and time 1.0
1 1 0.01158879
''')
            result=module.fields(path)
        self.assertEqual(sorted(result['displacements']),[.5,1.])
        self.assertEqual(result['displacements'][1.][1,1],.02)
        numpy.testing.assert_array_equal(result['equivalent plastic strain'][1.][0,:2],[1,1])
        self.assertAlmostEqual(result['equivalent plastic strain'][1.][0,2],.02-900/107000,places=7)

    @unittest.skipIf(numpy is None, 'Optional scientific runtime is unavailable')
    def test_selection_requires_every_case_finite_and_explicit_mass_ceiling(self):
        spec = importlib.util.spec_from_file_location('carrier_design_compare', SOURCE / 'compare.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        criteria = json.loads((SOURCE / 'normal-webs-selection-criteria.json').read_text())
        geometry = {'dense_reference_mass_kg': 1.25}
        inspection = {'central_pad_symmetric_difference_mm3': 0,
                      'end_interface_symmetric_difference_mm3': {str(i): 0 for i in range(6)},
                      'study_assembly_screen_pass': True}
        rows = [{'mesh': mesh, 'case': case, 'metrics': {
            metric: {'candidate': 9, 'V6f': 10}
            for metric in ('displacement_max_mm', 'integration_point_VM_max_MPa')}}
            for mesh in criteria['mechanics']['meshes'] for case in criteria['mechanics']['cases']]
        result = module.select(criteria, geometry, inspection, rows, True)
        self.assertTrue(result['selection_pass'])
        self.assertFalse(result['original_mass_ceiling_pass'])
        original = json.loads((SOURCE / 'selection-criteria.json').read_text())
        self.assertFalse(module.select(original, geometry, inspection, rows, True)['selection_pass'])
        rows[0]['metrics']['displacement_max_mm']['candidate'] = float('nan')
        self.assertFalse(module.select(criteria, geometry, inspection, rows, True)['selection_pass'])
        rows[0]['metrics']['displacement_max_mm']['candidate'] = 11
        self.assertFalse(module.select(criteria, geometry, inspection, rows, True)['selection_pass'])
        rows[0]['metrics']['displacement_max_mm']['candidate'] = 9
        rows[1] = rows[0]
        self.assertFalse(module.select(criteria, geometry, inspection, rows, True)['selection_pass'])


if __name__ == '__main__':
    unittest.main()
