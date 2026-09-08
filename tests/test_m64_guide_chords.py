import importlib.util
import math
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/audit_guide_chords.py'
spec=importlib.util.spec_from_file_location('guide_chord_audit',PATH)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class GuideChordTests(unittest.TestCase):
    def test_strict_exact_crossing_and_orientation_invariance(self):
        segment=[('0.25','0.25','-1'),('0.25','0.25','1')]
        tri=[('0','0','0'),('1','0','0'),('0','1','0')]
        for s in (segment,segment[::-1]):
            for t in (tri,tri[::-1]):
                result=audit.exact_crossing(s,t)
                self.assertTrue(result['strict_interior_crossing_exact_for_saved_MSH'])
                self.assertEqual(result['exact_rational_parameters']['t'],'1/2')

    def test_boundary_touch_parallel_and_miss_are_not_claimed_proper(self):
        tri=[(0,0,0),(1,0,0),(0,1,0)]
        for segment in (((0,0,-1),(0,0,1)),((0,0,1),(1,0,1)),
                        ((2,2,-1),(2,2,1)),((0,0,0),(1,1,0))):
            self.assertIsNone(audit.exact_crossing(segment,tri))

    def test_short_chord_budget_preserves_margin_in_radial_gap(self):
        total=audit.sagitta(3.,.2)+audit.sagitta(3.015,.2)
        self.assertLess(total,.00334)
        self.assertLess(total,.015/4)
        self.assertGreater(.015-total,.01166)
        self.assertGreater(audit.sagitta(3.015,.707901971719416),.015)
        for bad in (-1,float('nan'),float('inf'),6.):
            with self.assertRaises(ValueError):audit.sagitta(3.,bad)

    def test_triangle_spanning_axis_uses_whole_interior_not_edge_bound(self):
        tri=[(3*math.cos(a),3*math.sin(a),0) for a in (0,2*math.pi/3,4*math.pi/3)]
        self.assertEqual(audit.radial_triangle_minimum(tri,(0,0,1)),0.)
        thin=[(3.,0.,0.),(3.,.1,0.),(3.,-.1,0.)]
        self.assertAlmostEqual(audit.radial_triangle_minimum(thin,(0,0,1)),3.)

    def test_pure_gate_rejects_coarse_chords_but_accepts_local_fine_envelope(self):
        for angle,accepted in ((.03,True),(.3,False)):
            frames={'domain_sha256':audit.DOMAIN_SHA,'faces_private':[]};points={};triangles={}
            for fid in audit.FACES:
                radius=3.015 if fid in (55,58) else 3.
                frames['faces_private'].append({'face_id':fid,'face_sha256':audit.FACE_SHAS[fid],
                    'radius':radius,'axis_point_private':[0.,0.,0.],'axis_direction_private':[0.,0.,1.],
                    'native_max_tolerance':1e-7})
                ids=[]
                for a,z in ((-angle,0.),(angle,0.),(0.,.2)):
                    n=len(points)+1;points[n]=(radius*math.cos(a),radius*math.sin(a),z);ids.append(n)
                triangles[fid]=[tuple(ids)]
            result=audit.mesh_chord_gate(points,triangles,frames)
            self.assertEqual(result['local_radial_envelopes_accepted'],accepted)
            frames['faces_private'][0]['face_sha256']='bad'
            with self.assertRaises(ValueError):audit.mesh_chord_gate(points,triangles,frames)


if __name__=='__main__':unittest.main()
