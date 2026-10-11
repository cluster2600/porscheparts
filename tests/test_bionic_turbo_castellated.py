import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "twins/bionic-turbo-f1/cfd"))
import prepare_case
import prepare_castellated
import check_cartesian_cells
import run_cartesian_pilot
from test_bionic_turbo_f1_cfd import surface as tetra_surface


class CastellatedCaseTests(unittest.TestCase):
    def test_diagnostic_runner_fails_closed_and_retains_native_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            (case / "0").mkdir()
            (case / "0/U").write_text("original")
            manifest = {"image": prepare_case.IMAGE, "file_sha256": {"0/U": prepare_case.sha(case / "0/U")}}
            (case / "case-manifest.json").write_text(json.dumps(manifest))
            proof = {"schema": "bionic-cartesian-diagnostic-admission/v1", "status": "cartesian_geometry_proven",
                     "source_sha256": prepare_case.sha(Path(check_cartesian_cells.__file__)),
                     "case_manifest_sha256": prepare_case.sha(case / "case-manifest.json"),
                     "diagnostic_solver_authorized": True, "performance_ranking_authorized": False,
                     "proof": {"all_cells_axis_aligned_boxes": True}, "mesh": {"mesh_sha256": {}}}
            (case / "cartesian-proof.json").write_text(json.dumps(proof))
            self.assertIn("0/U", run_cartesian_pilot.verify(case))
            (case / "0/U").write_text("changed")
            with mock.patch.object(run_cartesian_pilot.subprocess, "run") as native:
                with self.assertRaises(ValueError):
                    run_cartesian_pilot.run(case)
                native.assert_not_called()
            (case / "0/U").write_text("original")
            with mock.patch.object(run_cartesian_pilot.subprocess, "run", return_value=mock.Mock(returncode=1)) as native:
                report = run_cartesian_pilot.run(case)
                self.assertEqual(report["status"], "failed")
                self.assertFalse(report["performance_ranking_authorized"])
                self.assertIn("--network", native.call_args_list[0].args[0])
                self.assertEqual(native.call_count, 2)
            with self.assertRaises(ValueError):
                run_cartesian_pilot.run(case)

    def test_cartesian_proof_accepts_split_coplanar_face_but_rejects_distortion(self):
        points = np.array([(0,0,0),(1,0,0),(1,1,0),(0,1,0),
                           (0,0,1),(1,0,1),(1,1,1),(0,1,1),(0.5,0,0),(0.5,1,0)]) * .001
        faces = [np.array(f) for f in ((0,3,9,8),(8,9,2,1),(4,5,6,7),
                                      (0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))]
        owners = np.zeros(len(faces), dtype=int)
        neighbours = np.array([], dtype=int)
        result = check_cartesian_cells.box_proof(points, faces, owners, neighbours)
        self.assertTrue(result["all_cells_axis_aligned_boxes"])
        self.assertAlmostEqual(result["total_box_volume_m3"], 1e-9)
        with self.assertRaises(ValueError):
            check_cartesian_cells.box_proof(points, faces[:-1], owners[:-1], neighbours)
        with self.assertRaises(ValueError):
            check_cartesian_cells.box_proof(points, [faces[0][::-1], *faces[1:]], owners, neighbours)
        distorted = points.copy()
        distorted[6, 2] += .0001
        with self.assertRaises(ValueError):
            check_cartesian_cells.box_proof(distorted, faces, owners, neighbours)

    def test_only_snapping_changes_and_inputs_remain_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            surface = root / "surface.stl"
            surface.write_text(tetra_surface())
            output = root / "case"
            manifest = prepare_castellated.prepare(surface, output)
            original = prepare_case.case_files(manifest["surface"], "medium", 100000, 1, 1.2, 800)
            for name, content in original.items():
                expected = content.replace("snap true;", "snap false;") if name == "system/snappyHexMeshDict" else content
                self.assertEqual((output / name).read_text(), expected)
                self.assertEqual(prepare_case.sha(output / name), manifest["file_sha256"][name])
            self.assertFalse(manifest["performance_ranking_authorized"])
            self.assertFalse(manifest["diagnostic_recipe"]["snapping"])
            self.assertEqual(json.loads((output / "case-manifest.json").read_text()), manifest)
            with self.assertRaises(FileExistsError):
                prepare_castellated.prepare(surface, output)
