import importlib.util
import copy
import math
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/audit_guide_chords.py'
spec=importlib.util.spec_from_file_location('guide_chord_audit',PATH)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def fixture(angle=.03,bad_face=None):
    cylinders=[];points={};triangles={}
    groups={55:('intake_1','walls_guide',[0.,12.]),57:('intake_1','walls_guide',[12.,35.]),
            63:('intake_1','walls_valve',[0.,12.]),61:('intake_1','walls_valve',[12.,35.]),
            56:('intake_2','walls_guide',[0.,12.]),58:('intake_2','walls_guide',[12.,35.]),
            64:('intake_2','walls_valve',[0.,12.]),62:('intake_2','walls_valve',[12.,35.])}
    for fid in audit.FACES:
        component,role,bounds=groups[fid];radius=3.015 if role=='walls_guide' else 3.
        row={'face_id':fid,'face_sha256':audit.FACE_SHAS[fid],'component':component,'role':role,
            'radius':radius,'axis_point_private':[0.,0.,0.],'axis_direction_private':[0.,0.,1.],
            'native_axial_parameter_bounds':bounds,'native_max_tolerance':1e-7,
            'BRep_face_valid':True,'full_cylindrical_band_verified_numeric':True}
        cylinders.append(row);ids=[];local_angle=.3 if fid==bad_face else angle
        for a,z in ((-local_angle,bounds[0]+.1),(local_angle,bounds[0]+.1),(0.,bounds[0]+.3)):
            n=len(points)+1;points[n]=(radius*math.cos(a),radius*math.sin(a),z);ids.append(n)
        triangles[fid]=[tuple(ids)]
    for fid,component,bounds in ((65,'intake_1',[-14.,0.]),(66,'intake_2',[-14.,0.]),
            (67,'intake_1',[-14.01,-14.]),(68,'intake_2',[-14.01,-14.]),
            (69,'intake_1',[-17.,-14.01]),(70,'intake_2',[-17.,-14.01])):
        row=copy.deepcopy(cylinders[4]);row.update(face_id=fid,face_sha256='excluded-fixture',
            component=component,role='walls_valve',radius=3.,native_axial_parameter_bounds=bounds)
        cylinders.append(row)
    frames={'schema':'m64-native-guide-cylinder-frames/v2','domain_sha256':audit.DOMAIN_SHA,
        'native_inventory':{'native_face_count':len(cylinders),'all_native_faces_examined':True,
            'surface_types':[{'face_id':r['face_id'],'surface_type':'GeomAbs_Cylinder'} for r in cylinders],
            'cylinders_private':cylinders},'coverage':audit.gap_portion_inventory(cylinders),
        'faces_private':[r for r in cylinders if r['face_id'] in audit.FACES]}
    return points,triangles,frames


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
            points,triangles,frames=fixture(angle)
            result=audit.mesh_chord_gate(points,triangles,frames)
            self.assertEqual(result['local_radial_envelopes_accepted'],accepted)
            frames['faces_private'][0]['face_sha256']='bad'
            with self.assertRaises(ValueError):audit.mesh_chord_gate(points,triangles,frames)

    def test_worst_portion_controls_whole_component_not_old_four_pairs(self):
        points,triangles,frames=fixture(bad_face=57)
        result=audit.mesh_chord_gate(points,triangles,frames)
        groups={g['component']:g for g in result['groups']}
        self.assertFalse(groups['intake_1']['accepted_local_radial_envelope'])
        self.assertTrue(groups['intake_2']['accepted_local_radial_envelope'])
        self.assertEqual(groups['intake_1']['guide_faces'],[55,57])
        self.assertEqual(groups['intake_1']['stem_faces'],[61,63])

    def test_below_guide_stems_remain_in_inventory_with_explicit_exclusions(self):
        points,triangles,frames=fixture();coverage=frames['coverage']
        self.assertEqual(coverage['selected_face_ids'],list(audit.FACES))
        notes={r['face_id']:r for r in coverage['excluded_cylinders']}
        self.assertEqual(set(notes),{65,66,67,68,69,70})
        self.assertIn('boundary_touch',notes[65]['reason'])
        self.assertEqual(notes[69]['reason'],'no_axial_overlap_with_inner_guide')
        for group in coverage['groups']:
            self.assertAlmostEqual(sum(r['covered_stem_length'] for r in group['guide_axial_coverage']),35.)

    def test_missing_portion_or_inventoried_extra_overlap_cannot_pass(self):
        points,triangles,frames=fixture();frames['faces_private'].pop()
        with self.assertRaises(ValueError):audit.mesh_chord_gate(points,triangles,frames)
        points,triangles,frames=fixture()
        frames['native_inventory']['cylinders_private']=[r for r in frames['native_inventory']['cylinders_private'] if r['face_id']!=56]
        with self.assertRaises(ValueError):audit.mesh_chord_gate(points,triangles,frames)
        points,triangles,frames=fixture()
        next(r for r in frames['native_inventory']['cylinders_private'] if r['face_id']==65)['native_axial_parameter_bounds']=[-14.,1.]
        frames['coverage']=audit.gap_portion_inventory(frames['native_inventory']['cylinders_private'])
        with self.assertRaises(ValueError):audit.mesh_chord_gate(points,triangles,frames)

    def test_partial_band_or_wrong_axis_cannot_use_interval_coverage(self):
        for key,value in (('full_cylindrical_band_verified_numeric',False),('axis_point_private',[1.,0.,0.])):
            points,triangles,frames=fixture();frames['native_inventory']['cylinders_private'][0][key]=value
            with self.assertRaises(ValueError):audit.gap_portion_inventory(frames['native_inventory']['cylinders_private'])

    def test_axial_coverage_hole_and_wrong_component_are_rejected(self):
        points,triangles,frames=fixture();rows=frames['native_inventory']['cylinders_private']
        next(r for r in rows if r['face_id']==61)['native_axial_parameter_bounds']=[13.,35.]
        with self.assertRaises(ValueError):audit.gap_portion_inventory(rows)
        points,triangles,frames=fixture();rows=frames['native_inventory']['cylinders_private']
        next(r for r in rows if r['face_id']==56)['component']=None
        with self.assertRaises(ValueError):audit.gap_portion_inventory(rows)

    def test_remapped_Gmsh_entity_tags_preserve_the_native_gate(self):
        points,triangles,frames=fixture();mapping={fid:9001+i for i,fid in enumerate(audit.FACES)}
        raw=[{'tag':i+1,'face':mapping[fid],'nodes':tri} for i,(fid,rows) in enumerate(triangles.items()) for tri in rows]
        report={'import':{'face_binding_private':{'descriptor_bijection_verified':True,
            'matches_private':[{'source_face_index':fid,'gmsh_face_tag':tag} for fid,tag in mapping.items()]}}}
        rebound=audit.bind_triangles_to_native(raw,report,audit.FACES)
        grouped={fid:[t['nodes'] for t in rebound if t['face']==fid] for fid in audit.FACES}
        self.assertEqual(audit.mesh_chord_gate(points,triangles,frames),audit.mesh_chord_gate(points,grouped,frames))
        report['import']['face_binding_private']['matches_private'].pop()
        with self.assertRaises(ValueError):audit.bind_triangles_to_native(raw,report,audit.FACES)


if __name__=='__main__':unittest.main()
