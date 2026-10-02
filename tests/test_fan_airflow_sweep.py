"""Keep geometric experiments distinct from flow predictions."""
import json
import os
from pathlib import Path
import runpy
import sys
import subprocess
import tempfile
import unittest
from _deps import require_modules

SOURCE = Path(__file__).resolve().parents[1] / "twins/993-engine-cooling-fan-system-f0/source"


class FanSweepTests(unittest.TestCase):
    def test_monitor_exits_for_completed_case_without_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            case = Path(folder)
            (case / "system").mkdir()
            (case / "system/controlDict").write_text("stopAt endTime;")
            (case / "log.foamRun").write_text("\nEnd\n")
            result = subprocess.run([sys.executable, str(SOURCE / "monitor_reference_cfd.py"), str(case)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Ended without usable convergence windows", result.stdout)
            self.assertEqual((case / "system/controlDict").read_text(), "stopAt endTime;")

    def test_bad_rotating_interface_never_starts_solver(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("system", "constant/polyMesh", "bin", "audit_fan_mrf_interface"):
                (root / name).mkdir(parents=True)
            (root / "system/controlDict").touch()
            (root / "constant/polyMesh/boundary").write_text("rotor { type wall; }\nduct { type wall; }\n")
            for name, body in {
                "checkMesh": 'echo "Mesh OK."', "topoSet": "exit 0", "wmake": "exit 0",
                "auditFanMRFInterface": 'echo "MRF REJECTED: internal interface is not tangent to rotation"; exit 2',
                "decomposePar": "touch solver-would-start",
            }.items():
                command = root / "bin" / name
                command.write_text("#!/bin/sh\n" + body + "\n")
                command.chmod(0o755)
            script = root / "run.sh"
            script.write_text((SOURCE / "run_reference_cfd.sh").read_text().replace(
                "source /opt/openfoam14/etc/bashrc", ": # test utilities on PATH"))
            result = subprocess.run(["bash", str(script), str(root), "--existing-mesh"],
                env=os.environ | {"PATH": str(root / "bin") + os.pathsep + os.environ["PATH"]}, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("not tangent to rotation", (root / "log.mrf-interface").read_text())
            self.assertFalse((root / "solver-would-start").exists())

    def test_velocity_plot_rejects_clipped_or_invalid_colour_scales(self):
        require_modules("numpy", "matplotlib", "torch", "physicsnemo")
        with tempfile.TemporaryDirectory() as folder:
            vtk = Path(folder) / "plane.vtk"
            vtk.write_text("# vtk DataFile Version 2.0\nplane\nASCII\nDATASET POLYDATA\n"
                "POINTS 3 float\n0 0 0 1 0 0 0 0 1\nPOLYGONS 1 4\n3 0 1 2\n"
                "CELL_DATA 1\nFIELD attributes 2\np 1 1 float\n0\nU 3 1 float\n0 0 2\n")
            command = [sys.executable, str(SOURCE / "plot_fan_velocity.py"), str(vtk)]
            result = subprocess.run(command + ["--speed-max", "3"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(vtk.with_suffix(".png").is_file())
            for maximum in ("1", "nan", "inf", "0"):
                result = subprocess.run(command + ["--speed-max", maximum], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Colour maximum must", result.stderr)

    def test_failed_extended_mesh_never_starts_solver(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "system").mkdir()
            (root / "system/controlDict").touch()
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name, body in {
                "blockMesh": "exit 0", "snappyHexMesh": "exit 0",
                "checkMesh": 'if [ "$#" = 0 ]; then echo "Mesh OK."; else echo "Failed 1 mesh checks."; fi',
                "topoSet": 'touch solver-would-start',
            }.items():
                command = bin_dir / name
                command.write_text("#!/bin/sh\n" + body + "\n")
                command.chmod(0o755)
            script = root / "run.sh"
            script.write_text((SOURCE / "run_reference_cfd.sh").read_text().replace(
                "source /opt/openfoam14/etc/bashrc", ": # test utilities on PATH"))
            result = subprocess.run(["bash", str(script), str(root)],
                env=os.environ | {"PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / "solver-would-start").exists())

    def test_imported_mesh_is_walled_and_rejected_before_solver(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "system").mkdir()
            (root / "system/controlDict").touch()
            (root / "fluid.msh").touch()
            bin_dir = root / "bin"
            bin_dir.mkdir()
            commands = {
                "gmshToFoam": 'mkdir -p constant/polyMesh; printf "rotor { type patch; }\\nduct { type patch; }\\n" > constant/polyMesh/boundary',
                "checkMesh": 'echo "Failed 1 mesh checks."',
                "topoSet": 'touch solver-would-start',
            }
            for name, body in commands.items():
                command = bin_dir / name
                command.write_text("#!/bin/sh\n" + body + "\n")
                command.chmod(0o755)
            script = root / "run.sh"
            script.write_text((SOURCE / "run_reference_cfd.sh").read_text().replace(
                "source /opt/openfoam14/etc/bashrc", ": # test utilities on PATH"))
            result = subprocess.run(["bash", str(script), str(root), str(root / "fluid.msh")],
                env=os.environ | {"PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual((root / "constant/polyMesh/boundary").read_text().count("type wall;"), 2)
            self.assertFalse((root / "solver-would-start").exists())
            (bin_dir / "gmshToFoam").write_text("#!/bin/sh\nexit 99\n")
            result = subprocess.run(["bash", str(script), str(root), "--existing-mesh"],
                env=os.environ | {"PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]}, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse((root / "solver-would-start").exists())

    def test_controlled_plan_preserves_interfaces_and_prior_outputs(self):
        module = runpy.run_path(str(SOURCE / "sweep_fan_airflow.py"))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "plan"
            module["plan"](output)
            plan = json.loads((output / "plan.json").read_text())
            self.assertEqual(len(plan["variants"]), 16)
            base = json.loads((output / "e-control.json").read_text())
            for name, changes in plan["variants"].items():
                candidate = json.loads((output / (name + ".json")).read_text())
                for key in plan["fixed"]:
                    self.assertEqual(candidate[key], base[key])
                differences = {k: v for k, v in candidate.items()
                               if k != "parameter_evidence" and v != base[k]}
                self.assertEqual(differences, changes)
            with self.assertRaises(FileExistsError):
                module["plan"](output)

    def test_warp_ray_kernel_has_known_hit_and_miss(self):
        require_modules("warp", "trimesh", "numpy")
        import numpy as np
        import trimesh
        import warp as wp
        sys.path.insert(0, str(SOURCE))
        try:
            from warp_fan_screen import axial_hits
            box = trimesh.creation.box(extents=(2, 2, 2))
            mesh = wp.Mesh(points=wp.array(box.vertices.astype(np.float32), dtype=wp.vec3, device="cpu"),
                           indices=wp.array(box.faces.astype(np.int32).ravel(), dtype=wp.int32, device="cpu"))
            origins = wp.array([[0, 0, -10], [3, 0, -10]], dtype=wp.vec3, device="cpu")
            hits = wp.zeros(2, dtype=wp.int32, device="cpu")
            wp.launch(axial_hits, 2, inputs=[mesh.id, origins, hits], device="cpu")
            self.assertEqual(hits.numpy().tolist(), [1, 0])
        finally:
            sys.path.pop(0)
