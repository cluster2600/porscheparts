import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'twins/bionic-turbo-f1/cfd'))
import mrf_interface_countertrial as trial
import test_bionic_turbo_transient as fixtures


class InterfaceCountertrialTests(unittest.TestCase):
    def test_zone_only_change_and_rejects_native_geometry_mutation(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                parent = fixtures.TransientPilotTests().parent(root)
                mesh = parent / 'constant/polyMesh'
                mesh.mkdir()
                (mesh / 'points').write_text('geometry sentinel')
                (mesh / 'cellZones').write_text('old zone')
                proof_path = parent / 'cartesian-proof.json'
                proof = json.loads(proof_path.read_text())
                proof['mesh']['mesh_sha256'] = {str(p.relative_to(parent)): trial.sha(p) for p in mesh.iterdir()}
                proof_path.write_text(json.dumps(proof))
                output = root / 'countertrial'

                def native(*args, **kwargs):
                    (output / 'constant/polyMesh/cellZones').write_text('new zone')
                    if corrupt:
                        (output / 'constant/polyMesh/points').write_text('changed')
                    return mock.Mock(returncode=0)

                def inspect(case, expected):
                    return {'mesh_sha256': {str(p.relative_to(case)): trial.sha(p) for p in (case / 'constant/polyMesh').iterdir()},
                            'rotor_owner_cells_all_in_zone': True, 'ports_outside_zone': True}

                before = trial.verify(parent)
                with mock.patch.object(trial.subprocess, 'run', side_effect=native), mock.patch.object(trial, 'inspect_mesh', side_effect=inspect):
                    if corrupt:
                        with self.assertRaisesRegex(ValueError, 'geometry or connectivity'):
                            trial.prepare(parent, output)
                        continue
                    trial.prepare(parent, output)
                self.assertEqual(before, trial.verify(parent))
                self.assertIn('radius .038;', (output / 'system/topoSetDict').read_text())
                for name in ('0/U', '0/p', '0/T', 'constant/MRFProperties'):
                    self.assertEqual((output / name).read_bytes(), (parent / name).read_bytes())
                self.assertIn('default Euler;', (output / 'system/fvSchemes').read_text())
                self.assertFalse((output / '0/phi').exists())
                self.assertFalse(json.loads((output / 'cartesian-proof.json').read_text())['performance_ranking_authorized'])
                with self.assertRaises(FileExistsError):
                    trial.prepare(parent, output)
