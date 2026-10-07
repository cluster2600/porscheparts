"""Independent equilibrium and energy checks for hypothesis calculations."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0,str(SOURCE))
spec = importlib.util.spec_from_file_location('hypothesis_tests',SOURCE/'run_hypothesis_tests.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.remove(str(SOURCE))
CARD = {'id': 'alsi10mg', 'density_g_cm3': 2.67, 'young_modulus_GPa': 70}


class HypothesisTests(unittest.TestCase):
    def test_annulus_free_boundaries_and_radial_equilibrium(self):
        for r in (0.02,0.1375):
            self.assertAlmostEqual(module.annulus(CARD,8500,r)['radial_stress_pa'],0,places=7)
        r,h = 0.07,1e-7
        state = module.annulus(CARD,8500,r)
        derivative = (module.annulus(CARD,8500,r+h)['radial_stress_pa']-
                      module.annulus(CARD,8500,r-h)['radial_stress_pa'])/(2*h)
        body_force = 2670*(8500*math.pi/30)**2*r
        self.assertAlmostEqual((derivative+(state['radial_stress_pa']-state['hoop_stress_pa'])/r)/body_force,-1,places=8)
        with self.assertRaises(ValueError): module.annulus(CARD,True)

    def test_scenario_conserves_power_and_braking_energy_without_promotion(self):
        case,mass = module.make_case(CARD,6000,0.1,0.5)
        result = module.twin.calculate(case)
        models = {k:v['values'] for k,v in result['models'].items()}
        dynamics = models['inertia_and_unbalance']
        # Constant deceleration: average speed is half the initial speed.
        braking_work = abs(dynamics['rotor_acceleration_torque_nm'])*(6000*math.pi/30)/2*0.1
        self.assertAlmostEqual(braking_work,dynamics['rotor_kinetic_energy_j'])
        flow,drive = models['airflow'],models['steady_drive_budget']
        self.assertAlmostEqual(drive['steady_drive_loss_w']+flow['fan_shaft_power_w'],drive['steady_drive_input_power_w'])
        self.assertAlmostEqual(sum(flow['branch_volume_flow_m3_s']),flow['volume_flow_m3_s'])
        self.assertGreater(mass,0)
        self.assertFalse(result['manufacturing_release_allowed'])
        case['purpose']='specimen_model'
        case['specimen_id']='unverified'
        with self.assertRaises(ValueError): module.twin.calculate(case)


if __name__ == '__main__':
    unittest.main()
