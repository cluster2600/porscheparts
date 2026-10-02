"""Opt-in acceptance fixtures for the reviewed, immutable external DfAM tool.

No download, installation, head geometry or manufacturing verdict in this test.
Set M64_DFAM_TOOL to the pinned upstream script; use an isolated mesh runtime.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = os.environ.get('M64_DFAM_TOOL')
TOOL_SHA = '48b3cbcfe55f7f02d59bb7b8030d9384e04e032d012eed0af0203bb7989e44a6'


@unittest.skipUnless(TOOL and importlib.util.find_spec('trimesh'),
                     'optional reviewed external DfAM tool and geometry runtime')
class ExternalDfAMTests(unittest.TestCase):
    def test_exact_cli_on_known_solid_assembly_orientations_and_invalid_mesh(self):
        import trimesh
        path = Path(TOOL)
        self.assertFalse(path.is_symlink())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), TOOL_SHA)
        with tempfile.TemporaryDirectory(prefix='m64-dfam-fixtures-') as folder:
            root = Path(folder)

            def run(mesh, command='measure'):
                source = root/'fixture.stl'
                mesh.export(source)
                result = subprocess.run([sys.executable, str(path), command, str(source)],
                                        capture_output=True, text=True, timeout=60, check=False)
                return result.returncode, json.loads(result.stdout)

            cube = trimesh.creation.box(extents=[10., 10., 10.])
            code, report = run(cube)
            self.assertEqual(code, 0, report)
            self.assertFalse(report['partial'])
            self.assertEqual(report['mesh']['volume_mm3'], 1000.)
            self.assertEqual(report['wall_thickness']['min_mm'], 10.)
            self.assertEqual(report['support_volume']['estimated_support_volume_mm3'], 0.)
            code, orientations = run(cube, 'orientations')
            self.assertEqual(code, 0, orientations)
            self.assertEqual(len(orientations['orientations']['candidates']), 6)
            self.assertTrue(all(row['build_height_mm'] == 10.
                                for row in orientations['orientations']['candidates']))

            lower = trimesh.creation.box(extents=[10., 10., .2])
            upper = trimesh.creation.box(extents=[10., 10., .3])
            upper.apply_translation([0, 0, .2/2+.03+.3/2])
            code, report = run(trimesh.util.concatenate([lower, upper]))
            self.assertEqual(code, 0, report)
            self.assertEqual(report['mesh']['body_count'], 2)
            self.assertEqual(sorted(row['min_mm'] for row in report['wall_thickness']['per_body']), [.2, .3])
            # A 0.03 mm assembly clearance must not be reported as material thickness.
            self.assertGreater(report['wall_thickness']['min_mm'], .03)

            plane = trimesh.Trimesh(vertices=[[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                                    faces=[[0, 1, 2]], process=False)
            code, report = run(plane)
            self.assertEqual(code, 2, report)
            self.assertTrue(report['partial'])
            self.assertFalse(report['mesh']['watertight'])
            self.assertIn('wall_thickness', report['partial_sections'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), TOOL_SHA)


if __name__ == '__main__': unittest.main()
