import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy'),'optional numerical helper dependencies')
class AcuteBlendTest(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('gmsh'),'optional mesh runtime')
    def test_chamber_frontal_override_rejects_another_body(self):
        import argparse
        import hashlib
        import json
        import sys
        import tempfile
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))
        import screen_tip_cut_surface as screen
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'candidate-private.brep').write_bytes(b'not the pinned chamber')
            (root/'report.json').write_text(json.dumps(dict(candidate_sha256=hashlib.sha256(b'not the pinned chamber').hexdigest(),
                inputs_unchanged=True,status='candidate_pending_BOP_distance_and_mesh')))
            args=argparse.Namespace(reference_body=None,candidate=root,output=root/'output',
                surface_algorithm=1,chamber_frontal=True,minimum=.00002,cpu_seconds=540)
            with self.assertRaisesRegex(ValueError,'exact_chamber_network_and_meshadapt_background_required'):
                screen.run(args)
            self.assertFalse(args.output.exists())

    def test_local_candidate_admission_requires_every_guard(self):
        path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/trial_acute_cylinder_blend.py'
        spec=importlib.util.spec_from_file_location('acute_blend',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        good=dict(native_valid=True,protected_unchanged=True,source_in_memory_unchanged=True,
                  tolerances_not_increased=True,solid_count=1)
        self.assertTrue(module.admitted(good,(141,142),{2,140,141,142},{2,140,141,142}))
        for key in good:
            bad=dict(good);bad.pop(key)
            self.assertFalse(module.admitted(bad,(141,142),{141,142},{141,142}))
        self.assertFalse(module.admitted({**good,'native_valid':1},(141,142),{141,142},{141,142}))
        self.assertFalse(module.admitted(good,(141,142),{141,142},{141,142,999}))
        self.assertFalse(module.admitted(good,(141,142),{141,142},{141}))
        self.assertFalse(module.admitted(good,(2,142),{2,142},{2,142}))
        self.assertTrue(module.admitted({**good,'crease_seams_without_cusp':True},(2,142),{2,142},{2,142}))

    @unittest.skipUnless(importlib.util.find_spec('OCP'),'optional CAD runtime')
    def test_material_crease_has_two_oriented_tangent_seams(self):
        import math
        path=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody/trial_acute_cylinder_blend.py'
        spec=importlib.util.spec_from_file_location('acute_blend',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        from trial_bounded_tip_cut import encode
        from build_bounded_c1_trunk import adaptive_volume
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
        from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.TopAbs import TopAbs_EDGE,TopAbs_FACE
        from OCP.TopoDS import TopoDS
        from OCP.gp import gp_Pnt,gp_Vec
        poly=BRepBuilderAPI_MakePolygon(); turn=math.radians(8.); radius=.5
        for x,z in ((-1.,0.),(0.,0.),(1.,math.tan(turn)),(1.,1.),(-1.,1.)):
            poly.Add(gp_Pnt(x,0.,z))
        poly.Close()
        body=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(poly.Wire()).Face(),gp_Vec(0.,1.,0.)).Shape()
        before=encode(body); chosen=[]
        for raw in module.indexed(body,TopAbs_EDGE):
            edge=TopoDS.Edge_s(raw); curve=BRepAdaptor_Curve(edge)
            if all(abs(p.X())+abs(p.Z())<1e-12 for p in
                   (curve.Value(curve.FirstParameter()),curve.Value(curve.LastParameter()))): chosen.append(edge)
        self.assertEqual(len(chosen),1)
        supports=[f for f in module.indexed(body,TopAbs_FACE)
                  if any(chosen[0].IsSame(e) for e in module.indexed(f,TopAbs_EDGE))]
        op,_=module.build_fillet(body,chosen,radius,'strict-approximation-v1')
        self.assertTrue(op.IsDone()); self.assertTrue(BRepCheck_Analyzer(op.Shape(),True,False,True).IsValid())
        rows=module.crease_seams(op,chosen[0],supports)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['sampled_tangent_under_0p1_degree'] for r in rows))
        self.assertTrue(all(r['continuous_tangency_certified'] is False for r in rows))
        removed=adaptive_volume(body)[0]-adaptive_volume(op.Shape())[0]
        self.assertAlmostEqual(removed,radius**2*(math.tan(turn/2)-turn/2),places=12)
        self.assertEqual(encode(body),before)
        from audit_shared_curve_consistency import tangent_group
        result=module.indexed(op.Shape(),TopAbs_FACE)
        members=list(op.Generated(chosen[0]))+[f for support in supports for f in op.Modified(support)]
        selected=[i for i,f in enumerate(result,1) if any(f.IsSame(g) for g in members)]
        self.assertEqual(len(selected),3)
        audit=tangent_group(result,selected)
        self.assertEqual(len(audit['internal_seams']),2)
        self.assertTrue(audit['all_internal_seams_screened'])
        self.assertFalse(audit['continuous_tangency_certified'])
        with self.assertRaises(ValueError): tangent_group(result,selected+selected[:1])
        flipped=list(result); flipped[selected[0]-1]=flipped[selected[0]-1].Reversed()
        with self.assertRaisesRegex(ValueError,'opposed_internal_seam'):
            tangent_group(flipped,selected)
        with self.assertRaisesRegex(ValueError,'sharp_unannotated'):
            tangent_group(result,list(range(1,len(result)+1)))
