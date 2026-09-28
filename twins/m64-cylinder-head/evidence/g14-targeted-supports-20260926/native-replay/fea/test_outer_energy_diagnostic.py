"""Small analytic checks, no production field integration or FE solve."""
import tempfile
from pathlib import Path
import unittest

import outer_energy_diagnostic as audit


class EnergyDiagnostic(unittest.TestCase):
    def test_isotropic_energy_and_global_gate(self):
        s=100.;E=audit.E;nu=audit.NU
        self.assertAlmostEqual(float(audit.density([s,0,0,0,0,0])),s*s/(2*E))
        self.assertAlmostEqual(float(audit.density([s,s,s,0,0,0])),3*(1-2*nu)*s*s/(2*E))
        self.assertAlmostEqual(float(audit.density([0,0,0,s,0,0])),(1+nu)*s*s/E)
        self.assertTrue(audit.balance(1.,1.)['passed'])
        self.assertFalse(audit.balance(1.01,1.)['passed'])
        with self.assertRaises(ValueError):audit.balance(float('nan'),1.)

    def test_affine_C3D10_volume_positions_and_curved_rejection(self):
        np=audit.np
        corners=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        xyz=np.concatenate((corners,np.array([(corners[a]+corners[b])/2 for a,b in audit.EDGES])))[None,:,:]
        volumes,positions,error=audit.tetra_geometry(xyz)
        self.assertAlmostEqual(float(volumes[0]),1/6)
        np.testing.assert_allclose(positions.mean(axis=1),[[.25,.25,.25]],atol=1e-14)
        np.testing.assert_allclose(positions[0,0],[audit.BETA]*3,atol=1e-14)
        self.assertEqual(error,0.)
        xyz[0,4,0]+=.001
        with self.assertRaises(ValueError):audit.tetra_geometry(xyz)

    def test_stress_gp_requires_exactly_four_unique_points(self):
        header=' stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set EALL\n'
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'test.dat'
            path.write_text(header+''.join(f'7 {ip} 1 2 3 4 5 6\n' for ip in (1,2,3,4)))
            self.assertEqual(audit.stress_gp(path,{7:[]}).shape,(1,4,6))
            path.write_text(header+''.join(f'7 {ip} 1 2 3 4 5 6\n' for ip in (1,2,3,3)))
            with self.assertRaises(ValueError):audit.stress_gp(path,{7:[]})
            path.write_text(header+'7 1 1 2 3 4 5 6\n')
            with self.assertRaises(ValueError):audit.stress_gp(path,{7:[]})


if __name__=='__main__':unittest.main()
