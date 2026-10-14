from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from audit_parallel_diagnostic import require_completed

class ParallelAuditTests(unittest.TestCase):
    def test_native_completion_needs_solve_and_reconstruction(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'native-exit.json').write_text('{"exit_code":0}')
            (p/'log.transient-rhoPimpleFoam').write_text('native output\nEnd\n\nFinalising parallel run\n')
            (p/'log.reconstructPar').write_text('reconstructed\nEnd\n')
            require_completed(p)
            (p/'log.reconstructPar').write_text('partial')
            with self.assertRaises(ValueError):require_completed(p)
            (p/'log.reconstructPar').write_text('End\n')
            (p/'log.transient-rhoPimpleFoam').write_text('FOAM FATAL\nEnd\nFinalising parallel run\n')
            with self.assertRaises(ValueError):require_completed(p)
            (p/'log.transient-rhoPimpleFoam').write_text('native\nEnd\nFinalising parallel run\n')
            (p/'native-exit.json').write_text('{"exit_code":65}')
            with self.assertRaises(ValueError):require_completed(p)
