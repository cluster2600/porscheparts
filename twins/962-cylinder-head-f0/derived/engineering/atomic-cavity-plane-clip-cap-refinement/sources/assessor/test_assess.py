"""Tiny fabricated saved-output checks only; no native/actual cap output execution."""
import importlib.util
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cap_assess',HERE/'assess.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
LITERAL=HERE.parent/'atomic-cavity-plane-clip-cap-refinement-prep-001/fixture-expectations.json'

class SavedCap(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        case=json.loads(LITERAL.read_text())['cases']['ordinary'];self.points=[tuple(x)for x in case['literal_points_mm']];self.faces=[tuple(x)for x in case['literal_oriented_faces']]
        self.cap=self.root/'cap.bin';self.map=self.root/'map.u64';self.fixed=self.root/'fixed.u64';self.out=self.root/'out';self.out.mkdir()
        self.cap.write_bytes(self.surface(self.points,self.faces));self.map.write_bytes(struct.pack('<QQ',0,0));self.fixed.write_bytes(struct.pack('<Q',5))
        self.origins=list(range(8));self.sources=[a.MAX]*8;self.sources[5]=5;self.new=0
        self.write_positive()

    @staticmethod
    def surface(points,faces):return b'962SURF1'+struct.pack('<QQ',len(points),len(faces))+b''.join(struct.pack('<ddd',*p)for p in points)+b''.join(struct.pack('<QQQ',*t)for t in faces)
    def save_report(self):
        (self.out/'report.json').write_text(json.dumps(self.report,allow_nan=False)+'\n')
    def write_positive(self):
        (self.out/'cap-candidate.bin').write_bytes(self.surface(self.points,self.faces))
        (self.out/'vertex-coordinate-origins.u64').write_bytes(b''.join(struct.pack('<Q',v)for v in self.origins))
        (self.out/'face-source-ids.u64').write_bytes(b''.join(struct.pack('<Q',v)for v in self.sources))
        m=a.functions();rows,p,t=m['read'](self.cap);old_area,_,_=a.exact_faces(p,t,m['need'],False);_,cycles,_=a.planar(t,len(p),m)
        constraints={tuple(sorted((loop[i],loop[(i+1)%len(loop)])))for loop in cycles for i in range(len(loop))}|{tuple(sorted((t[5][i],t[5][(i+1)%3])))for i in range(3)}
        _,q,outfaces=m['read'](self.out/'cap-candidate.bin');area,q2,poor=a.exact_faces(q,outfaces,m['need'],True)
        self.report=dict(status='cap_only_local_candidate',stage='complete',reason='Fabricated exact known-result fixture, not native',input_vertices=8,input_faces=8,map_rows=1,identity_map_rows=1,nonidentity_map_rows=0,fixed_faces=1,constrained_edges=len(constraints),shape_aspect_bound=.125,size_bound=0,refinement_attempts=self.new,requests_with_one_insertion=self.new,requests_without_insertion=0,no_insertion_causes_separately_instrumented=False,active_shape_bad_before=1,active_shape_bad_after=1,output_vertices=len(q),output_faces=len(outfaces),new_interior_points=self.new,final_exact_faces_below_2_over_29=poor,before_quality=dict(triangles=8,below_necessary_bound=0,minimum_triangle_SICN=.4),after_quality=dict(triangles=len(outfaces),below_necessary_bound=0,minimum_triangle_SICN=math.sqrt(float(q2))),original_cap_area=str(old_area),mapped_cap_area=str(area),embedded_cap_area=str(area),original_cap_cycles=cycles,mapped_cap_cycles=cycles,guards=dict.fromkeys(a.GUARDS,True),exported=True,candidate_file_present=True,interior_Steiner_hypothesis=True,policy_old_coordinate_bits_required=True,new_point_and_nonfixed_face_provenance_sentinel=a.MAX,CGAL_CDT_active_shape_criteria_satisfied=False,original_vs_mapped_domain_equality_claimed=False,head_surface_or_solver_admitted=False,manufacturing_authorized=False)
        self.save_report()
    def bindings(self):return {str(p):a.sha(p)for p in[self.cap,self.map,self.fixed]+list(self.out.iterdir())}
    def run_assess(self,rc=0,bindings=None):return a.assess(self.cap,self.map,self.fixed,self.out,rc,self.bindings()if bindings is None else bindings)
    def test_identity_known_annulus_and_native_shape_not_fulfilled(self):
        result=self.run_assess();self.assertEqual(result['exact_cap_area_mm2'],'12');self.assertEqual(result['fixed_faces'],1);self.assertEqual(result['new_interior_points'],0)
        self.assertFalse(self.report['CGAL_CDT_active_shape_criteria_satisfied'])
    def test_known_new_interior_sentinel_and_complete_counts(self):
        t=self.faces[0];xyz=tuple(sum(self.points[v][k]for v in t)/3 for k in range(3));self.points.append(xyz)
        self.faces=[(t[0],t[1],8),(t[1],t[2],8),(t[2],t[0],8)]+self.faces[1:]
        self.origins.append(a.MAX);self.sources=[a.MAX]*len(self.faces);self.sources[7]=5;self.new=1;self.write_positive()
        result=self.run_assess();self.assertEqual(result['new_interior_points'],1);self.assertEqual(result['topology']['faces'],10)
    def test_modified_data_without_updated_manifest_refused(self):
        bindings=self.bindings();self.report['output_vertices']=9;self.save_report()
        with self.assertRaisesRegex(ValueError,'external frozen hashes'):self.run_assess(bindings=bindings)
    def test_rehashed_wrong_counts_and_old_coordinate_bits_refused(self):
        self.report['output_faces']=9;self.save_report()
        with self.assertRaisesRegex(ValueError,'output counts'):self.run_assess()
        self.report['output_faces']=8;self.save_report();self.points[0]=(-2.125,-2,0);(self.out/'cap-candidate.bin').write_bytes(self.surface(self.points,self.faces))
        with self.assertRaisesRegex(ValueError,'original bits'):self.run_assess()
    def test_rehashed_fixed_provenance_and_reversed_face_refused(self):
        (self.out/'face-source-ids.u64').write_bytes(struct.pack('<Q',a.MAX)*8)
        with self.assertRaisesRegex(ValueError,'relabelled new'):self.run_assess()
        self.write_positive();self.faces[0]=self.faces[0][::-1];(self.out/'cap-candidate.bin').write_bytes(self.surface(self.points,self.faces))
        with self.assertRaises(ValueError):self.run_assess()
    def refusal(self):
        for p in self.out.iterdir():
            if p.name!='report.json':p.unlink()
        self.report.update(status='rejected_no_candidate',stage='original_annular_cap',reason='Known invalid fixed association',guards={},exported=False,candidate_file_present=False,CGAL_CDT_active_shape_criteria_satisfied=False,output_vertices=0,output_faces=0)
        self.save_report()
    def test_report_only_refusal_credits_no_initialized_zeros(self):
        self.refusal();r=self.run_assess(3);self.assertTrue(r['later_guards_and_initialized_zero_counters_unobserved'])
        self.report['guards'][a.GUARDS[-1]]=True;self.save_report()
        with self.assertRaisesRegex(ValueError,'Stage-aware'):self.run_assess(3)
    def test_rehashed_boolean_quality_count_refused(self):
        self.report['after_quality']['below_necessary_bound']=False;self.save_report()
        with self.assertRaisesRegex(ValueError,'Typed finite'):self.run_assess()
    def test_refusal_extra_export_and_nonfinite_JSON_refused(self):
        self.refusal();(self.out/'cap-candidate.bin').write_bytes(b'not accepted')
        with self.assertRaisesRegex(ValueError,'closure'):self.run_assess(3)
        (self.out/'cap-candidate.bin').unlink();(self.out/'report.json').write_text(json.dumps(self.report)[:-1]+',"unobserved":1e999}')
        with self.assertRaisesRegex(ValueError,'Finite complete'):self.run_assess(3)

if __name__=='__main__':unittest.main()
