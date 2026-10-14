import hashlib
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from audit_interface_corridor import bounds, corridor, read_patches


class CorridorTests(unittest.TestCase):
    def row(self,z,lo,hi):
        return dict(z_low_mm=z,z_high_mm=z+1,rotor_upper_mm=lo,stator_lower_mm=hi)

    def test_faces_not_only_vertices_bound_stator(self):
        rotor=np.array([[[1,0,0],[1,0,.1],[1,.01,.1]]])
        stator=np.array([[[-3,1,0],[3,1,0],[0,1,.1]]])
        r=bounds(rotor,stator)
        self.assertLessEqual(r[0]['stator_lower_mm'],1)
        self.assertLess(r[0]['gap_lower_mm'],0)

    def test_missing_stator_stays_unresolved(self):
        rotor=np.array([[[1,0,0],[1,0,.1],[1,.01,.1]]])
        r=bounds(rotor,rotor+[0,0,10])
        self.assertIsNone(r[0]['stator_lower_mm'])
        self.assertEqual(corridor(r)['open_profiles'],[])
        for value in (0,float('nan'),2):
            with self.assertRaises(ValueError):bounds(rotor,rotor,value)

    def test_chords_stay_between_bounds_in_both_adjacent_bands(self):
        rows=[self.row(0,2,4),self.row(1,3,5),self.row(2,2,4)]
        result=corridor(rows,8);p=result['open_profiles'][0]
        for i,row in enumerate(rows):
            radii=[v[1] for v in p['nodes_z_radius_mm'][i:i+2]]
            self.assertGreater(min(radii)*math.cos(math.pi/8),row['rotor_upper_mm'])
            self.assertLess(max(radii),row['stator_lower_mm'])
        self.assertFalse(result['closed_interface_verified'])
        self.assertFalse(result['solver_admission_granted'])

    def test_positive_bands_do_not_guarantee_connected_corridor(self):
        result=corridor([self.row(0,1,2),self.row(1,3,4)])
        self.assertEqual(result['open_profiles'],[])
        self.assertEqual(len(result['failed_adjacent_intersections']),1)

    def test_unresolved_band_is_never_bridged(self):
        result=corridor([self.row(0,1,3),self.row(1,4,2),self.row(2,1,3)])
        self.assertEqual(result['unresolved_band_indices'],[1])
        self.assertEqual([x['band_indices'] for x in result['open_profiles']],[[0],[2]])

    def test_surface_digest_counts_and_finite_coordinates(self):
        text=''.join(f'solid {p}\nvertex 0 0 0\nvertex .001 0 0\nvertex 0 .001 .001\nendsolid {p}\n' for p in ('inlet','outlet','rotor','stator'))
        info=dict(region_triangles=dict.fromkeys(('inlet','outlet','rotor','stator'),1),closed_edges=True,sha256=hashlib.sha256(text.encode()).hexdigest())
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'surface.stl';path.write_text(text)
            self.assertEqual(read_patches(path,info)['rotor'].shape,(1,3,3))
            path.write_text(text+'changed\n')
            with self.assertRaises(ValueError):read_patches(path,info)
            bad=text.replace('vertex 0 0 0','vertex nan 0 0')
            path.write_text(bad);info['sha256']=hashlib.sha256(bad.encode()).hexdigest()
            with self.assertRaises(ValueError):read_patches(path,info)

class ProfileWitnessTests(unittest.TestCase):
    def test_sloped_facets_have_rotation_tangent_at_native_centroid(self):
        from audit_frame_interface import face_geometry
        for theta in np.linspace(0,2*math.pi,32,endpoint=False):
            angles=(theta,theta+2*math.pi/32)
            vertices=[[r*math.cos(t),r*math.sin(t),z] for r,z,ts in ((.029,.006,angles),(.028,.007,angles[::-1])) for t in ts]
            c,s=face_geometry(vertices)
            self.assertLess(abs(np.dot(np.cross([0,0,10471.975511966],c),s)/np.linalg.norm(s)),1e-11)

    def test_zone_is_explicit_and_invalid_profile_fails(self):
        from profile_mrf_witness import mesh_text
        text=mesh_text([[6,29],[6.5,28.5],[7,28]],.4,32)
        self.assertEqual(text.count('hex ('),128)
        self.assertEqual(text.count(') rotorZone ('),64)
        for nodes,width in (([[7,28],[6,29]],.4),([[6,29],[7,float('nan')]],.4),([[6,29],[7,28]],30)):
            with self.assertRaises(ValueError):mesh_text(nodes,width,32)

class PrecisionWitnessTests(unittest.TestCase):
    def test_only_native_write_precision_changes(self):
        import json
        from unittest.mock import patch
        import profile_mrf_witness_v3 as precise
        from prepare_case import sha
        with tempfile.TemporaryDirectory() as temporary:
            case=Path(temporary);(case/'system').mkdir()
            control=case/'system/controlDict';control.write_text('writePrecision 12; deltaT 1e-7;')
            manifest=dict(file_sha256={'system/controlDict':sha(control),'other':'unchanged'},profile_witness={})
            with patch.object(precise.previous,'prepare',return_value=manifest):
                result=precise.prepare(None,case,None,1)
                self.assertEqual(control.read_text(),'writePrecision 16; deltaT 1e-7;')
                self.assertEqual(result['file_sha256']['other'],'unchanged')
                self.assertEqual(result['file_sha256']['system/controlDict'],sha(control))
                self.assertEqual(json.loads((case/'manifest.json').read_text()),result)
                with self.assertRaises(ValueError):precise.prepare(None,case,None,1)
