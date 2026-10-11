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
import prepare_runtime_retry
import prepare_runtime_003
import prepare_runtime_004
import prepare_runtime_005
import prepare_runtime_006
from test_bionic_turbo_f1_cfd import surface as tetra_surface


class CastellatedCaseTests(unittest.TestCase):
    def test_diagnostic_runner_fails_closed_and_retains_native_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            (case / "0").mkdir()
            (case / "0/U").write_text("original")
            (case / "0/p").write_text("inlet {type totalPressure; psi psi;}")
            (case / "0/T").write_text("inlet {type totalTemperature; psi psi;}")
            (case / "constant").mkdir()
            (case / "constant/thermophysicalProperties").write_text("thermodynamics {Cp 1004.675; hf 0;}")
            (case / "system").mkdir()
            (case / "system/fvSolution").write_text("p {solver GAMG; smoother DIC; tolerance 1e-8;} SIMPLE {consistent yes;}")
            (case / "system/controlDict").write_text('yPlus {type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime;}')
            manifest = {"image": prepare_case.IMAGE, "file_sha256": {name: prepare_case.sha(case / name) for name in ("0/U", "0/p", "0/T", "constant/thermophysicalProperties", "system/fvSolution", "system/controlDict")}}
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
            retry = case / "retry"
            prepare_runtime_retry.prepare(case, retry)
            self.assertEqual((retry / "0/U").read_text(), "original")
            self.assertIn("hf 0;", (case / "constant/thermophysicalProperties").read_text())
            self.assertIn("Hf 0;", (retry / "constant/thermophysicalProperties").read_text())
            self.assertFalse((retry / "run-cartesian-solve.json").exists())
            with self.assertRaises(FileExistsError):
                prepare_runtime_retry.prepare(case, retry)
            corrected = case / "runtime003"
            prepare_runtime_003.prepare(case, corrected)
            for name in ("0/p", "0/T"):
                self.assertIn("psi thermo:psi;", (corrected / name).read_text())
                self.assertIn("psi psi;", (case / name).read_text())
            run_cartesian_pilot.verify(corrected)
            pcg = case / "runtime004"
            prepare_runtime_004.prepare(case, pcg)
            self.assertIn("solver PCG; preconditioner DIC; tolerance 1e-8;", (pcg / "system/fvSolution").read_text())
            self.assertIn("solver GAMG;", (case / "system/fvSolution").read_text())
            run_cartesian_pilot.verify(pcg)
            simple = case / "runtime005"
            prepare_runtime_005.prepare(case, simple)
            self.assertIn("consistent no;", (simple / "system/fvSolution").read_text())
            self.assertIn("solver GAMG;", (simple / "system/fvSolution").read_text())
            run_cartesian_pilot.verify(simple)
            observer = case / "runtime006"
            prepare_runtime_006.prepare(case, observer)
            self.assertIn("executeControl writeTime; writeControl writeTime;", (observer / "system/controlDict").read_text())
            self.assertEqual((simple / "system/fvSolution").read_bytes(), (observer / "system/fvSolution").read_bytes())
            run_cartesian_pilot.verify(observer)

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
