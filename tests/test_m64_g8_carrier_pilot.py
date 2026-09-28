"""G8 numerical plumbing checks; no physical release claim."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'twins/m64-cylinder-head/source/fourvalve'))
import g8_pilot as g8
import g8_iterative_retry as retry


class G8PilotChecks(unittest.TestCase):
    def test_quadratic_surface_loads_and_solver_vectors(self):
        points = {1:(0,0,0),2:(2,0,0),3:(0,2,0),4:(1,0,0),5:(1,1,0),6:(0,1,0)}
        weights, area = g8.surface_weights([[1,2,3,4,5,6]],points)
        self.assertEqual(area,2.)
        self.assertEqual(set(weights),{4,5,6})
        self.assertAlmostEqual(sum(weights.values()),1.)
        for v in weights.values():self.assertAlmostEqual(v,1/3)
        for tris in ([], [[1,1,1,4,5,6]], [[1,2,3]]):
            with self.assertRaises(ValueError):g8.surface_weights(tris,points)
        self.assertEqual(g8.ccx_tetra10(list(range(1,11))),[1,2,3,4,5,6,7,8,10,9])
        with self.assertRaises(ValueError):g8.ccx_tetra10([1]*10)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'test.dat'
            path.write_text(' forces (fx,fy,fz) for set SUPPORT\n\n1 -1 0 0\n2 -2 0 0\n\n'
                            ' stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz)\n1 1 1 0 0 0 0 0\n\n'
                            ' displacements (vx,vy,vz) for set NALL\n\n1 0.1 0 0\n2 0.2 0 0\n')
            self.assertEqual(g8.vectors(path,'forces ('),{1:(-1.,0.,0.),2:(-2.,0.,0.)})
            self.assertEqual(g8.parse_dat(path),([1.],[.1,.2]))
            path.write_text(' forces (fx,fy,fz)\n1 nan 0 0\n')
            with self.assertRaises(ValueError):g8.vectors(path,'forces (')
        deck = '*NODE\n1,-1,0,0\n2,1,0,0\n*STEP\n*STATIC\n*CLOAD\n1,1,5\n2,1,8\n*END STEP\n'
        points, loads = retry.deck_data(deck)
        self.assertEqual(set(points),{1,2});self.assertEqual(loads,{1:5.,2:8.})
        for bad in (deck.replace('1,1,5','1,3,5'),deck.replace('1,1,5','1,1,nan'),deck.replace('*STATIC','*DYNAMIC')):
            with self.assertRaises(ValueError):retry.deck_data(bad)

    def test_published_receipt_when_present(self):
        path = ROOT/'twins/m64-cylinder-head/evidence/g8-carrier-pilot-20260925/direct.partial.json'
        if not path.exists():self.skipTest('native pilot not published yet')
        report = json.loads(path.read_text())
        self.assertEqual(report['pilot_source_sha256'],g8.sha256(Path(g8.__file__)))
        self.assertEqual(report['baseline_sha256'],g8.sha256(g8.BASELINE))
        self.assertEqual(report['helper_sha256'],g8.sha256(ROOT/'twins/reference-917-engine/source/run_f37_carrier_calculix.py'))
        self.assertNotIn('complete',report)
        for key in ('manufacturing_authorized','engine_start_authorized','assembled_stiffness_qualified','material_selected'):
            self.assertFalse(report[key])
        self.assertEqual(len(report['cases']),5)
        self.assertLess(report['cases'][0]['reference_relative_error'],.05)
        for case in report['cases']:
            self.assertGreater(case['mesh']['minimum_Gauss4_Jacobian_mm3'],0)
            for result in case['solutions'].values():
                self.assertLess(result['force_balance_relative_error'],1e-4)
                self.assertLess(result['moment_balance_F_times_100mm_error'],1e-4)
                self.assertTrue(math.isfinite(result['maximum_displacement_mm']))
        result = json.loads(path.with_name('iterative-retry.json').read_text())
        self.assertEqual(result['partial_direct_report_sha256'],g8.sha256(path))
        self.assertEqual(result['source_sha256'],g8.sha256(Path(retry.__file__)))
        self.assertEqual(result['pilot_source_sha256'],g8.sha256(Path(g8.__file__)))
        self.assertEqual(result['rows'][0]['log_sha256'],g8.sha256(path.with_name('iterative-x.log')))
        self.assertFalse(result['full_three_mesh_two_direction_campaign_complete'])
        self.assertFalse(result['manufacturing_authorized']);self.assertFalse(result['engine_start_authorized'])
        self.assertFalse(result['retry_accepted'])
        self.assertGreater(result['rows'][0]['direct_solver_max_nodal_difference_over_max_U'],1e-4)
        self.assertFalse(result['rows'][0]['direct_reference_agreement_passed'])
        direct = report['cases'][-1]['files_sha256']
        self.assertEqual(result['rows'][0]['source_deck_sha256'],direct['x.inp'])
        self.assertEqual(result['rows'][0]['direct_reference_dat_sha256'],direct['x.dat'])
        self.assertEqual([r['size_mm'] for r in result['rows']],[3.])
        self.assertFalse(result['rows'][0]['equilibrium_passed'])
        self.assertGreater(result['rows'][0]['force_balance_relative_error'],1e-4)


if __name__ == '__main__':unittest.main()
