import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from static_mrf_witness import assess

class StaticMrfWitnessTests(unittest.TestCase):
    def test_equilibrium_drift_and_corrupt_histories(self):
        criteria={'max_abs_p_error_Pa':.001,'max_abs_T_error_K':1e-6,'max_speed_m_s':1e-8}
        rows=np.array([[1e-7,101325,298.15,0],[2e-7,101325,298.15,0]])
        self.assertTrue(assess(rows,rows,criteria)['stationary_equilibrium_reproduced'])
        drift=rows.copy();drift[1,2]-=.001
        self.assertFalse(assess(drift,rows,criteria)['stationary_equilibrium_reproduced'])
        speed=rows.copy();speed[1,3]=1e-4
        self.assertFalse(assess(rows,speed,criteria)['stationary_equilibrium_reproduced'])
        missing=rows.copy();missing[1,0]=3e-7
        with self.assertRaises(ValueError):assess(rows,missing,criteria)
        missing[1,0]=np.nan
        with self.assertRaises(ValueError):assess(rows,missing,criteria)

    def test_closed_cavity_uses_one_stationary_patch(self):
        import tempfile
        from unittest import mock
        import static_mrf_witness as witness
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);parent=root/'parent'
            for name in ('system/fvSchemes','system/fvSolution','constant/thermophysicalProperties'):
                p=parent/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture input')
            with mock.patch.object(witness,'verify',return_value={}):
                manifest=witness.prepare(parent,root/'case',0.)
            for name in ('U','p','T'):
                text=(root/'case/0'/name).read_text()
                self.assertIn('walls {type ',text)
                self.assertNotIn('inlet',text)
            self.assertFalse(manifest['performance_ranking_authorized'])
            self.assertIn('nonRotatingPatches (walls)',(root/'case/constant/MRFProperties').read_text())
