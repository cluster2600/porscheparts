import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/additivefoam'))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional numpy runtime')
class ThermalHistoryTests(unittest.TestCase):
    def test_complete_history_and_bad_grids(self):
        from audit_amb2018_thermal import series,field,FATAL
        self.assertIsNone(FATAL.search('sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).'))
        self.assertIsNotNone(FATAL.search('Floating point exception (core dumped)'))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'history'
            path.write_text('# test\n0 300\n.002 900\n.004 600\n')
            self.assertEqual(series(path).shape,(3,2))
            for content in ('0 300\n.004 nan\n','0 300\n.002 900\n','0 300\n0 400\n.004 600\n'):
                path.write_text(content)
                with self.assertRaises(ValueError): series(path)
            path.write_text('internalField nonuniform List<scalar> 56250 (300);')
            with self.assertRaises(ValueError): field(path)


if __name__=='__main__': unittest.main()
