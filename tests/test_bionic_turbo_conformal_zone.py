import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from prepare_case import case_files
from prepare_conformal_zone import zone_dictionary

class ConformalZoneTests(unittest.TestCase):
    def test_zone_is_generated_by_snapping_without_changing_physical_patches(self):
        files=case_files({'bounds_m':[[-.06,-.061,-.015],[.064,.08,.044]]},'medium',100000,1,1.2,800)
        source=files['system/snappyHexMeshDict'];result=zone_dictionary(source)
        self.assertIn('snap true;',result)
        self.assertIn('faceZone mrfInterface; cellZone rotorZone; cellZoneInside inside; faceType internal;',result)
        self.assertIn('point1 (0 0 -.004); point2 (0 0 .033); radius .038;',result)
        self.assertIn('allowFreeStandingZoneFaces false;',result)
        for patch in ('inlet','outlet','rotor','stator'):
            self.assertEqual(result.count(patch+' {'),source.count(patch+' {'))
        self.assertEqual(result.count('gapLevel'),source.count('gapLevel'))
        self.assertIn('minTetQuality 1e-12;',result)

    def test_unknown_or_duplicate_source_is_rejected(self):
        with self.assertRaises(ValueError):zone_dictionary('geometry {domain {')
        source='geometry {domain { geometry {domain { refinementSurfaces {domain { allowFreeStandingZoneFaces true;'
        with self.assertRaises(ValueError):zone_dictionary(source)

class FramePolygonTests(unittest.TestCase):
    def test_subdividing_straight_edge_preserves_native_centroid_and_flux(self):
        import numpy as np
        from audit_frame_interface import face_geometry
        a=np.array([[2,0,0],[2,2,0],[2,2,3],[2,0,3]],dtype=float)
        b=np.insert(a,1,[2,.25,0],axis=0)
        ca,sa=face_geometry(a);cb,sb=face_geometry(b)
        np.testing.assert_allclose(ca,[2,1,1.5],atol=1e-14)
        np.testing.assert_allclose(sa,[6,0,0],atol=1e-14)
        np.testing.assert_allclose(cb,ca,atol=1e-14)
        np.testing.assert_allclose(sb,sa,atol=1e-14)
        cr,sr=face_geometry(b[::-1]);np.testing.assert_allclose(cr,ca,atol=1e-14);np.testing.assert_allclose(sr,-sa,atol=1e-14)

    def test_triangle_and_degenerate_polygon(self):
        import numpy as np
        from audit_frame_interface import face_geometry
        c,s=face_geometry([[0,0,0],[3,0,0],[0,3,0]])
        np.testing.assert_allclose(c,[1,1,0]);np.testing.assert_allclose(s,[0,0,4.5])
        for p in ([[0,0,0]]*4,[[0,0,0],[1,0,0],[2,0,0]],[[0,0,0],[1,0,0],[float('nan'),1,0]]):
            with self.assertRaises(ValueError):face_geometry(p)

class ConformalPreparationTests(unittest.TestCase):
    def test_surface_copy_and_existing_destination_are_protected(self):
        import json,tempfile
        from unittest.mock import patch
        import prepare_conformal_zone as module
        with tempfile.TemporaryDirectory() as temporary,patch.object(module,'verify') as verify:
            root=Path(temporary);parent=root/'parent';surface=parent/'constant/triSurface/domain.stl';surface.parent.mkdir(parents=True)
            surface.write_bytes(b'copy integrity fixture')
            info={'sha256':module.base.sha(surface),'bounds_m':[[-.06,-.061,-.015],[.064,.08,.044]]}
            (parent/'case-manifest.json').write_text(json.dumps({'surface':info}))
            output=root/'trial';manifest=module.prepare(parent,output)
            self.assertEqual((output/'constant/triSurface/domain.stl').read_bytes(),surface.read_bytes())
            self.assertTrue(manifest['mesh_only']);self.assertFalse(manifest['performance_ranking_authorized'])
            self.assertIn('actions ();',(output/'system/topoSetDict').read_text())
            before=(output/'case-manifest.json').read_bytes()
            with self.assertRaises(FileExistsError):module.prepare(parent,output)
            self.assertEqual((output/'case-manifest.json').read_bytes(),before)
            surface.write_bytes(b'changed')
            with self.assertRaises(ValueError):module.prepare(parent,root/'tampered')
            self.assertFalse((root/'tampered').exists())
            self.assertEqual(verify.call_count,3)

class NativeAddressingTests(unittest.TestCase):
    def test_largest_cell_may_appear_only_as_a_neighbour(self):
        import numpy as np
        from audit_frame_interface_v2 import cell_flags
        np.testing.assert_array_equal(cell_flags(np.array([0,0]),np.array([2,1]),np.array([2])),[False,False,True])
        with self.assertRaises(ValueError):cell_flags(np.array([0]),np.array([1]),np.array([2]))
        with self.assertRaises(ValueError):cell_flags(np.array([0]),np.array([-1]),np.array([0]))
