"""A short arc must never become a confidently reconstructed full bore."""
import unittest
try:
    import numpy as np
    import scipy.optimize
    HAS_GEOMETRY = True
except ImportError:
    HAS_GEOMETRY = False
if HAS_GEOMETRY:
    from scripts.cad_recode.recover_sections import fit_circle


@unittest.skipUnless(HAS_GEOMETRY, 'dedicated geometry runtime required')
class CircleRecoveryTest(unittest.TestCase):
    def test_circle_and_false_arc(self):
        angles = np.linspace(0, 2*np.pi, 256, endpoint=False)
        points = np.c_[3+20*np.cos(angles), -7+20*np.sin(angles)]
        good = fit_circle(points, .1)
        self.assertTrue(good['retained'])
        self.assertAlmostEqual(good['radius'], 20, places=6)
        np.testing.assert_allclose(good['center'], [3,-7], atol=1e-6)
        self.assertFalse(fit_circle(points[:64], .1)['retained'])
        ellipse = points * [1, .7]
        self.assertFalse(fit_circle(ellipse, .1)['retained'])
        with self.assertRaises(ValueError):
            fit_circle(np.full((50,2), np.nan), .1)

@unittest.skipUnless(HAS_GEOMETRY, 'dedicated geometry runtime required')
class PlanarBoundaryTest(unittest.TestCase):
    def test_hole_remains_and_branch_is_rejected(self):
        from scripts.cad_recode.recover_planes import boundary, loops_from_boundary
        # Four quadrants of a square annulus, with separate inner and outer loops.
        triangles = np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],
                              [2,3,7],[2,7,6],[3,0,4],[3,4,7]])
        loops = loops_from_boundary(boundary(triangles))
        self.assertEqual(sorted(map(len,loops)),[4,4])
        with self.assertRaises(ValueError):
            loops_from_boundary(np.array([[0,1],[1,2],[2,0],[0,3],[3,4],[4,0]]))


@unittest.skipUnless(HAS_GEOMETRY, 'dedicated geometry runtime required')
class RepairTriangulationTest(unittest.TestCase):
    def test_concave_gap_preserves_boundary_and_area(self):
        from scripts.cad_recode.repair_scan_gaps import triangulate_polygon
        from scripts.cad_recode.recover_planes import boundary
        points = np.array([[0,0],[2,0],[2,1],[1,1],[1,2],[0,2]], dtype=float)
        for polygon in (points,points[::-1]):
            faces = triangulate_polygon(polygon)
            self.assertEqual(len(faces),4)
            edges = boundary(faces)
            self.assertEqual(len(edges),6)
            self.assertEqual(set(map(tuple,edges)),{tuple(sorted((i,(i+1)%6))) for i in range(6)})
            area = sum(abs(np.linalg.det(np.stack([polygon[b]-polygon[a],polygon[c]-polygon[a]])))/2 for a,b,c in faces)
            self.assertAlmostEqual(area,3)
        with self.assertRaises(ValueError):
            triangulate_polygon([[0,0],[1,0],[2,0]])


@unittest.skipUnless(HAS_GEOMETRY, 'dedicated geometry runtime required')
class ScanGapRepairTest(unittest.TestCase):
    @unittest.skipUnless(__import__('importlib').util.find_spec('trimesh'), 'CAD runtime required')
    def test_fill_interior_gap_and_preserve_functional_opening(self):
        import json
        import tempfile
        from pathlib import Path
        import trimesh
        from scripts.cad_recode.pipeline import digest
        from scripts.cad_recode.repair_scan_gaps import repair
        points = np.array([[x,y,0] for y in range(5) for x in range(5)],dtype=float)
        faces = []
        for y in range(4):
            for x in range(4):
                if (x,y)==(1,1): continue
                a=y*5+x
                faces.extend([[a,a+1,a+6],[a,a+6,a+5]])
        # A small isolated scan fragment is not a hole: do not cap its back.
        points = np.vstack([points,[[10,0,0],[11,0,0],[10,1,0]]])
        faces.append([25,26,27])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'raw.obj'
            trimesh.Trimesh(points,faces,process=False).export(source)
            profiles=root/'profiles.json'
            profiles.write_text(json.dumps({'source_sha256':digest(source),'profiles':[]}))
            repair(source,profiles,root/'fixed',digest(source))
            report=json.loads((root/'fixed/repair.json').read_text())
            self.assertEqual(report['filled_gaps'],1)
            self.assertEqual(report['added_triangles'],2)
            self.assertEqual(report['boundary_edges_before']-report['boundary_edges_after'],4)
            profiles.write_text(json.dumps({'source_sha256':digest(source),'profiles':[
                {'center':[1.5,1.5,0],'normal':[0,0,1],'radius':1}]}))
            with self.assertRaisesRegex(ValueError,'no unprotected gap'):
                repair(source,profiles,root/'protected',digest(source))


if __name__ == '__main__':
    unittest.main()
