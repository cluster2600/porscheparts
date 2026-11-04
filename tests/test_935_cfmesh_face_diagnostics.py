"""Independent small-mesh checks for the 935 wall-incidence diagnostics."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'twins/935-horizontal-cooling-system-f0/source/cfmesh-face-location-20261104'


class FaceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mesh = Path(self.tmp.name)
        (self.mesh / 'sets').mkdir()
        (self.mesh / 'boundary').write_text('rotor { nFaces 2; startFace 4; }\n')
        (self.mesh / 'owner').write_text('6\n(\n0\n1\n2\n5\n0\n1\n)\n')
        (self.mesh / 'neighbour').write_text('6\n(\n1\n2\n3\n6\n-1\n-1\n)\n')
        (self.mesh / 'sets' / 'selected').write_text('4\n(\n0\n1\n2\n3\n)\n')

    def run_script(self, name):
        return subprocess.run([sys.executable, str(SRC / name), str(self.mesh), 'selected'],
                              text=True, capture_output=True)

    def test_owner_neighbour_and_distinct_wall_faces(self):
        run = self.run_script('adjacency_screen.py')
        self.assertEqual(run.returncode, 0, run.stderr)
        entry = json.loads(run.stdout)['sets']['selected']
        self.assertEqual((entry['owner_incident'], entry['neighbour_incident'],
                          entry['both_incident'], entry['either_incident']), (2, 1, 1, 2))
        self.assertEqual((entry['rotor_owner_cells_incident'], entry['rotor_faces_incident']), (2, 2))

    def test_adjacency_rejects_a_boundary_face_in_internal_set(self):
        (self.mesh / 'sets' / 'selected').write_text('1\n(\n4\n)\n')
        self.assertNotEqual(self.run_script('adjacency_screen.py').returncode, 0)

    def test_classifier_rejects_duplicate_face_ids(self):
        (self.mesh / 'sets' / 'selected').write_text('2\n(\n0\n0\n)\n')
        self.assertNotEqual(self.run_script('classify_faces.py').returncode, 0)

    def test_whole_edge_connectivity_not_vertex_contact(self):
        sys.path.insert(0, str(SRC))
        self.addCleanup(sys.path.remove, str(SRC))
        from wall_components import component_sizes
        self.assertEqual(component_sizes([[0,1,2], [2,1,3], [3,4,5], [5,4,6], [10,11,12]]), [2,2,1])


if __name__ == '__main__':
    unittest.main()
