"""Private trust and recipe guards; no real mesh, CCX or CG execution."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scipy.sparse import csr_matrix
import next_candidates as c


class NextCandidateTrust(unittest.TestCase):
    def test_real_two_cad_chains_and_combined_geometry(self):
        for ident in c.IDS:
            _, variant, proof = c.inputs(ident)
            self.assertEqual(variant['journal_width_mm'],11 if ident==c.CENTRE else 8)
            self.assertTrue(proof['combined_geometry']['pairwise_no_intersection'])
            self.assertFalse(proof['mounting_and_maintenance_qualified'])

    def test_changed_input_or_rejected_cad_cannot_pass(self):
        path = c.HERE.parent/c.SPECS[c.CENTRE]['folder']/'receipt.json'
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory)/'receipt.json'; changed.write_text(path.read_text()+' ')
            with self.assertRaises(ValueError): c.inputs(c.CENTRE,changed)
        row = json.loads(path.read_text())['variants'][0]
        row['cad_accepted'] = False
        with self.assertRaises(ValueError): c.core.accepted(row,{},row['baseline_step_sha256'])

    def test_missing_reference_stops_before_any_worker_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(reference=Path(directory)/'missing.json',output=Path(directory)/'never-created')
            with patch.object(c.subprocess,'Popen') as spawn:
                with self.assertRaises(FileNotFoundError): c.run(args)
                spawn.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_audit_uses_public_900second_cap_and_rejects_bad_residual(self):
        prefix = '*NODE\n1,0,0,0\n2,1,0,0\n*NSET,NSET=SUPPORT\n1\n*MATERIAL,NAME=GENERIC\n*ELASTIC\n70000,.33\n*SOLID SECTION,ELSET=EALL,MATERIAL=GENERIC\n'
        step = '*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n2,{d},1\n*END STEP\n'
        for bad in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name,d in (('x',1),('minus_z',3)):
                    (root/(name+'.inp')).write_text(prefix+step.format(d=d))
                    (root/(name+'.dat')).write_text('mock only, not FE evidence')
                for name in ('matrix.sti','matrix.dof'): (root/name).write_text('mock matrix')
                def solve(matrix,rhs,backend,max_seconds):
                    self.assertEqual(backend,'cpu'); self.assertEqual(max_seconds,900.)
                    return rhs*(2 if bad else 1),dict(info=0,dtype='float64')
                def compare(case,name,matrix,mapping,solution,rhs,points,support):
                    return dict(passed=solution['passed'],mechanics={'equilibrium_passed':True},agreement={})
                with patch.object(c.g9,'ccx',return_value=0), patch.object(c.g13,'serial_log',return_value={}), patch.object(c.bench,'read_matrix',return_value=(csr_matrix(c.np.eye(2)),[(2,1),(2,3)])), patch.object(c.bench,'solve',side_effect=solve), patch.object(c.reference,'compare',side_effect=compare):
                    rows = c.audit(root,c.time.monotonic()+3600)
                self.assertEqual(len(rows),1 if bad else 2)
                self.assertEqual(rows[0]['numerical_crosscheck_passed'],not bad)
                self.assertIn('*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY', (root/'matrix.inp').read_text())
                self.assertEqual((root/'matrix.inp').read_text().count('*STEP\n'),1)


if __name__ == '__main__':
    unittest.main()
