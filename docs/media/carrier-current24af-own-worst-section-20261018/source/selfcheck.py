"""Stdlib source/projection/scope fixtures only; no actual plotting or native imports."""
import ast,copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
s=importlib.util.spec_from_file_location('_current24af_section_figure_source_test',H/'render.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Contracts(unittest.TestCase):
 def face(self):return dict(face_index_zero_based=60,local_properties=dict(point_mm=[1.,2.,3.],local_chord=dict(status='unambiguous_first_native_in_out_normal_chord',thickness_mm=.5,target_face_index_zero_based=62),normal_line_intersections=[dict(face_index_zero_based=62,W_mm=.5,point_mm=[1.5,2.,3.])]))
 def test_original_IO_helpers_literal(self):
  v=json.loads((H/'source-reuse.json').read_text());a=(R/v['original']).read_text();b=(H/'render.py').read_text()
  for name in v['literal_helpers']:
   fn=lambda text:ast.get_source_segment(text,next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name));self.assertEqual(fn(a),fn(b))
 def test_exact_YZ_projection(self):self.assertEqual(m.yz([9.,2.,3.]),[2.,3.])
 def test_projection_keeps_actual_3D_length_and_endpoints(self):
  f=self.face();original=copy.deepcopy(f);r=m.projected_chord(f);self.assertEqual(r['start_xyz_mm'],[1.,2.,3.]);self.assertEqual(r['end_xyz_mm'],[1.5,2.,3.]);self.assertEqual(r['length_3D_mm'],.5);self.assertEqual(r['projected_start_YZ_mm'],r['projected_end_YZ_mm']);self.assertFalse(r['section_thickness_claimed']);self.assertEqual(f,original)
 def test_ambiguous_exact_endpoint_refused(self):
  f=self.face();f['local_properties']['normal_line_intersections']*=2
  with self.assertRaises(ValueError):m.projected_chord(f)
 def test_unqualified_support_refused(self):
  f=self.face();f['local_properties']['local_chord']=None
  with self.assertRaises(ValueError):m.projected_chord(f)
 def test_nonfinite_endpoints_refused(self):
  f=self.face();f['local_properties']['point_mm'][0]=float('inf')
  with self.assertRaises(ValueError):m.projected_chord(f)
 def test_all_native_curves_submitted(self):
  t=(H/'render.py').read_text();self.assertIn("for e in data['section']['edges']",t);self.assertIn('LineCollection(lines',t);self.assertNotIn('resample',t)
 def test_zoom_uses_actual_peak_element_bounds(self):
  t=(H/'render.py').read_text();self.assertIn("lo,hi=mesh_peak['corner_measure']['bounds_mm']",t);self.assertIn('([lo[1],hi[1]],[lo[2],hi[2]])',t)
 def test_projected_scope_explicit(self):
  t=(H/'render.py').read_text();self.assertIn('Y–Z projections of measured 3D normal chords',t);self.assertIn('not thicknesses of the displayed section',t);self.assertIn('endpoint X =',t)
 def test_all_other_native_rows_retained(self):
  t=(H/'render.py').read_text();self.assertIn("all_qualified_chords_retained=owner['exact_recomputed_chord_rows']",t);self.assertIn("all_unresolved_rows_retained=owner['retained_null_rows']",t)
 def test_no_kernel_or_extra_nice(self):
  t=(H/'render.py').read_text();calls={ast.unparse(n.func)for n in ast.walk(ast.parse(t))if isinstance(n,ast.Call)};self.assertFalse(calls&{'os.nice','BRepAlgoAPI_Section','BRepAlgoAPI_Cut','gmsh.model.mesh.generate'});self.assertNotIn('from OCP',t)
 def test_closed_actual_context_and_hashes(self):m.closed_data(json.loads((H/'pending-plan.json').read_text()))
 def test_pending_refuses_before_authoring(self):
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/'plan.json';p.write_bytes((H/'pending-plan.json').read_bytes())
   with self.assertRaisesRegex(ValueError,'NON-ARMED'):m.verify(p,m.sha(p),True)
 def test_no_plotting_or_scientific_import(self):self.assertFalse(set(sys.modules)&{'matplotlib','numpy','PIL','OCP','build123d','gmsh'})

 def test_reciprocal_pair_selection_skips_NULL_and_keeps_all_qualified(self):
  a=self.face();a['face_index_zero_based']=40;a['local_properties']['local_chord']['target_face_index_zero_based']=36;a['local_properties']['normal_line_intersections'][0]['face_index_zero_based']=36
  b=copy.deepcopy(a);b['face_index_zero_based']=36;b['local_properties']['local_chord']['target_face_index_zero_based']=40;b['local_properties']['normal_line_intersections'][0]['face_index_zero_based']=40
  n=copy.deepcopy(a);n['face_index_zero_based']=99;n['local_properties']['local_chord']=None
  native=dict(probes=[dict(nearest_faces=[a,n,b])]);old=copy.deepcopy(native);pairs,null=m.reciprocal_pairs(native)
  self.assertEqual([[x['source_face']for x in pair]for pair in pairs],[[40,36]]);self.assertEqual(len(null),1);self.assertEqual(native,old)
 def test_nonreciprocal_qualified_row_refuses(self):
  with self.assertRaisesRegex(ValueError,'reciprocal'):m.reciprocal_pairs(dict(probes=[dict(nearest_faces=[self.face()])]))
 def test_duplicate_qualified_source_refuses(self):
  f=self.face()
  with self.assertRaisesRegex(ValueError,'Duplicate'):m.reciprocal_pairs(dict(probes=[dict(nearest_faces=[f,copy.deepcopy(f)])]))
 def test_whole_renderer_inverse(self):
  import difflib
  d=json.loads((H/'source-changes.json').read_text());self.assertEqual(''.join(difflib.restore(d['whole_ndiff'],1)),(R/d['original']).read_text());self.assertEqual(''.join(difflib.restore(d['whole_ndiff'],2)),(H/'render.py').read_text())
 def test_pending_preserves_original_resource_runtime(self):
  p=json.loads((H/'pending-plan.json').read_text());old=json.loads((R/'work/carrier-R1-own-peak-section-figure-preparation-001/pending-plan.json').read_text());self.assertEqual(p['runtime_sha256'],old['runtime_sha256']);self.assertEqual(p['bounds'],old['bounds']);self.assertFalse(p['launch_ready']);self.assertIsNone(p['root_GO_sha256'])
 def test_current_closed_pairs_and_all_qualified_NULL_rows(self):
  p=json.loads((H/'pending-plan.json').read_text());data,native,owner=m.closed_data(p);pairs,null=m.reciprocal_pairs(native);self.assertEqual(len(pairs),2);self.assertEqual(sum(map(len,pairs)),4);self.assertEqual(len(null),4);self.assertEqual(len(owner['exact_recomputed_chord_rows']),8);self.assertEqual(len(owner['retained_null_rows']),32)
 def test_selected_all20_case_not_old_peak_index(self):
  t=(H/'prepare.py').read_text();self.assertIn("observer_plan['case_keys'].index(observer_plan['selected_case'])",t);self.assertNotIn("observer_plan['peak_files'][1]",t)

 def test_only_right_title_annotation_changed(self):
  d=json.loads((H/'source-changes.json').read_text());self.assertEqual(len(d['literal_replacements']),1);row=d['literal_replacements'][0];self.assertEqual(row['before'],"else'Actual peak-element bounds · Y–Z projection'");self.assertEqual(row['after'],"else'Actual peak-element bounds\\nY–Z projection'")
if __name__=='__main__':unittest.main(verbosity=2)
