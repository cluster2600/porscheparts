"""Exercise process/log gates without a CFD installation or private geometry."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = (Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/run_cfmesh_checked.py')


class MeshingGateTest(unittest.TestCase):
    def run_case(self, mesher, quality, mesh_exit=0, check_exit=0):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); case = root / 'case'; (case / 'system').mkdir(parents=True)
            (case / 'system' / 'meshDict').write_text('fixture')
            tools = root / 'bin'; tools.mkdir(); marker = root / 'check-started'
            for name, contents in [('cartesianMesh', mesher), ('checkMesh', quality)]:
                p = tools / name
                marker_code = f'open({str(marker)!r}, "w").close(); ' if name == 'checkMesh' else ''
                status = mesh_exit if name == 'cartesianMesh' else check_exit
                p.write_text(f'#!{sys.executable}\nimport sys\n{marker_code}print({contents!r}); sys.exit({status})\n')
                p.chmod(0o755)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ.get('PATH', ''))
            result = subprocess.run([sys.executable, str(SCRIPT), str(case), str(root / 'logs')], env=env, capture_output=True, text=True)
            return result.returncode, marker.exists()

    def test_silent_mesher_abort_does_not_start_check(self):
        self.assertEqual(self.run_case('Meshing process terminated!\nEnd', 'Mesh OK.\nEnd'), (1, False))

    def test_missing_renaming_and_nonzero_mesher_do_not_start_check(self):
        self.assertEqual(self.run_case('End', 'Mesh OK.\nEnd'), (1, False))
        self.assertEqual(self.run_case('Finished renaming boundary patches\nEnd', 'Mesh OK.\nEnd', mesh_exit=1), (1, False))

    def test_quality_failure_and_success(self):
        complete = 'Finished renaming boundary patches\nEnd'
        self.assertEqual(self.run_case(complete, 'Failed 4 mesh checks.\nEnd'), (1, True))
        self.assertEqual(self.run_case(complete, 'Mesh OK.\nEnd'), (0, True))
        self.assertEqual(self.run_case(complete, 'Mesh OK.\nEnd', check_exit=1), (1, True))


if __name__ == '__main__':
    unittest.main()
