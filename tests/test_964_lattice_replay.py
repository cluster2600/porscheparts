import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/"twins/964-chassis/monocoque/lattice-replay"
try:
    import numpy as np
except ImportError:
    np=None
if np is not None:
    sys.path.insert(0,str(STUDY))
    spec=importlib.util.spec_from_file_location("monocoque_replay_audit",STUDY/"audit.py")
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


@unittest.skipIf(np is None,"numpy unavailable")
class ReplayTests(unittest.TestCase):
    def test_centred_signed_volume_is_translation_invariant(self):
        p=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
        tri=p[[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]]
        self.assertAlmostEqual(audit.stable_volume(tri),1/6)
        self.assertAlmostEqual(audit.stable_volume(tri+np.array([-1728.,708.,864.])),1/6)
        self.assertAlmostEqual(audit.stable_volume(tri[:,::-1]),-1/6)
        for bad in (np.empty((0,3,3)),np.full((1,3,3),np.nan)):
            with self.assertRaises(ValueError):audit.stable_volume(bad)

    def test_exact_zero_screen_keeps_one_ulp_nonzero_triangle(self):
        tiny=np.nextafter(np.float32(0),np.float32(1)).item()
        triangles=np.array([[[0.,0,0],[1.,0,0],[0,0,0]],[[0.,0,0],[1.,0,0],[0,tiny,0]]])
        np.testing.assert_array_equal(audit.zero_mask(triangles),[True,False])

    @unittest.skipUnless(importlib.util.find_spec("scipy"),"scipy unavailable")
    def test_vertex_distance_ignores_face_order_but_not_displacement(self):
        from assess_phase import vertex_cloud_distance
        t=np.array([[[0.,0,0],[1.,0,0],[0,1.,0]],[[0.,0,1],[1.,0,1],[0,1.,1]]])
        self.assertEqual(vertex_cloud_distance(t,t[::-1,::-1]),0)
        self.assertAlmostEqual(vertex_cloud_distance(t,t+np.array([0.,0,4.])),4)
        with self.assertRaises(ValueError):vertex_cloud_distance(t,np.empty((0,3,3)))

    def test_interface_gate_does_not_fill_missing_coordinates(self):
        r=audit.survey_state(ROOT/"twins/964-chassis/derived/interface-measurements-20261008.csv")
        self.assertEqual(r["register_points"],18)
        self.assertEqual(r["validated_xyz"],0)
        self.assertEqual(len(r["missing_z"]),18)
        self.assertFalse(r["complete_body_interface_inventory"])

    @unittest.skipUnless(os.environ.get("REPLAY_DLL") and os.environ.get("DOTNET"),"native runtime not selected")
    def test_native_rejects_changed_contract_and_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            altered=Path(tmp)/"altered.json";altered.write_text("{}")
            out=Path(tmp)/"out"
            cmd=[os.environ["DOTNET"],os.environ["REPLAY_DLL"]]
            result=subprocess.run(cmd+[str(altered),str(out)],capture_output=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())
            self.assertIn(b"Only the archived nine-cell experiment",result.stderr)
            out.mkdir();sentinel=out/"keep";sentinel.write_text("keep")
            original=STUDY.parent/"field-lattice/evidence/report.json"
            result=subprocess.run(cmd+[str(original),str(out)],capture_output=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertEqual(sentinel.read_text(),"keep")
            self.assertIn(b"Output already exists",result.stderr)

    def test_retained_matrix_phase_and_intersection_evidence(self):
        ev=STUDY/"evidence"
        matrix=json.loads((ev/"replay-audit.json").read_text())
        phase=json.loads((ev/"phase-assessment.json").read_text())
        intersections=json.loads((ev/"intersections.json").read_text())
        self.assertTrue(matrix["archived_raw_triangle_coordinates_reproduced"])
        self.assertEqual([v["topology"]["exact_zero_area_faces"] for v in matrix["cases"].values()],[32,32,144,84])
        self.assertTrue(intersections["calibration_passed"])
        for label,row in phase["cases"].items():
            self.assertEqual(row["topology"]["exact_zero_area_faces"],0)
            self.assertTrue(row["topology"]["closed_oriented_combinatorial_surface_screen_pass"])
            self.assertEqual(row["topology"]["edge_connected_face_components"],1)
            self.assertEqual(row["topology"]["faces_removed"],0)
            self.assertTrue(intersections["cases"][label]["screen_passed"])
            self.assertEqual(intersections["cases"][label]["raw_stl_sha256"],row["raw_stl_sha256"])
            self.assertTrue(row["native"]["vdb_roundtrip_equal"])
            self.assertFalse(row["solver_ready"])
            for filename,key in (("raw.stl","raw_stl_sha256"),("raw.vdb","raw_vdb_sha256")):
                raw=gzip.decompress((ev/(label+"-"+filename+".gz")).read_bytes())
                self.assertEqual(hashlib.sha256(raw).hexdigest(),row[key])
        for r in (matrix,phase,intersections):
            for name,digest in r["source_sha256"].items():
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
            self.assertFalse(r["structural_analysis_executed"])
            self.assertFalse(r["manufacturing_authorized"])


if __name__=="__main__":unittest.main()
