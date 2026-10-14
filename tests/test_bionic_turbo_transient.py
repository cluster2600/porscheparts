import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "twins/bionic-turbo-f1/cfd"))
import check_cartesian_cells
import prepare_case
import prepare_castellated
import prepare_runtime_008
import transient_pilot
from test_bionic_turbo_f1_cfd import surface


class TransientPilotTests(unittest.TestCase):
    def parent(self, root):
        stl = root / "surface.stl"
        stl.write_text(surface())
        case = root / "original"
        prepare_castellated.prepare(stl, case)
        proof = {"schema": "bionic-cartesian-diagnostic-admission/v1", "status": "cartesian_geometry_proven",
                 "source_sha256": prepare_case.sha(Path(check_cartesian_cells.__file__)),
                 "case_manifest_sha256": prepare_case.sha(case / "case-manifest.json"),
                 "diagnostic_solver_authorized": True, "performance_ranking_authorized": False,
                 "proof": {"all_cells_axis_aligned_boxes": True}, "mesh": {"mesh_sha256": {}}}
        (case / "cartesian-proof.json").write_text(json.dumps(proof))
        parent = root / "runtime008"
        prepare_runtime_008.prepare(case, parent)
        return parent

    def test_transient_preserves_boundaries_and_parent_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = self.parent(root)
            before = transient_pilot.verify(parent)
            output = root / "transient"
            transient_pilot.prepare(parent, output)
            self.assertEqual(before, transient_pilot.verify(parent))
            for name in ("0/U", "0/p", "0/T", "constant/MRFProperties"):
                self.assertEqual((parent / name).read_bytes(), (output / name).read_bytes())
            self.assertIn("default Euler;", (output / "system/fvSchemes").read_text())
            self.assertNotIn("bounded Gauss", (output / "system/fvSchemes").read_text())
            self.assertIn("maxCo 0.3; maxDeltaT 1e-7;", (output / "system/controlDict").read_text())
            self.assertIn("PIMPLE", (output / "system/fvSolution").read_text())
            self.assertIn('"(rho|rhoFinal)" {solver diagonal;}', (output / "system/fvSolution").read_text())
            with self.assertRaises(FileExistsError):
                transient_pilot.prepare(parent, output)
            with mock.patch.object(transient_pilot.subprocess, "run", return_value=mock.Mock(
                    returncode=0, stdout="container-id", stderr="")) as native:
                report = transient_pilot.launch(output)
                self.assertFalse(report["performance_ranking_authorized"])
                self.assertIn("-d", native.call_args.args[0])
                self.assertNotIn("--rm", native.call_args.args[0])
                self.assertIn("7200", native.call_args.args[0][-1])
            with self.assertRaises(ValueError):
                transient_pilot.launch(output)
            (parent / "0/T").write_text("tampered")
            with self.assertRaises(ValueError):
                transient_pilot.prepare(parent, root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_watchdog_rejects_nonphysical_and_fatal_histories(self):
        for table, fatal in (("1 101325 -9\n", False), ("1 nan 298\n", False),
                             ("1 0 298\n", False), ("1 101325 298\n", True)):
            with self.subTest(table=table, fatal=fatal), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = root / "postProcessing/scalarMinima/0"
                data.mkdir(parents=True)
                (data / "volFieldValue.dat").write_text(table)
                # Stub only the executable and stdbuf; run the real shell watchdog.
                solver = root / "rhoPimpleFoam"
                solver.write_text("#!/bin/bash\n" + ("echo 'FOAM FATAL ERROR'\n" if fatal else "") + "sleep 12\n")
                solver.chmod(0o755)
                stdbuf = root / "stdbuf"
                stdbuf.write_text('#!/bin/bash\nshift 2\nexec "$@"\n')
                stdbuf.chmod(0o755)
                script = transient_pilot.SUPERVISOR.replace("cd /case || exit 90", "cd " + directory + " || exit 90")
                result = subprocess.run(["bash", "-c", script], cwd=root, timeout=20,
                                        env=dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"]),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 65, result.stderr)
                self.assertTrue((root / "rejection-reason.txt").exists())

    def test_terminal_receipt_requires_native_end_and_zero_exit(self):
        for native, expected in (("echo End > log.transient-rhoPimpleFoam", "native_completed_requires_history_audit"),
                                 ("echo partial > log.transient-rhoPimpleFoam", "failed"),
                                 ("exit 1", "failed")):
            with self.subTest(native=native), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                timeout = root / "timeout"
                timeout.write_text('#!/bin/bash\nshift 3\nexec "$@"\n')
                timeout.chmod(0o755)
                (root / "transient-supervisor.sh").write_text(native)
                entrypoint = transient_pilot.ENTRYPOINT.replace("cd /case || exit 90", "cd " + directory + " || exit 90")
                subprocess.run(["bash", "-c", entrypoint], cwd=root, timeout=10,
                               env=dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"]),
                               capture_output=True)
                receipt = json.loads((root / "native-exit.json").read_text())
                self.assertEqual(receipt["status"], expected)
                self.assertFalse(receipt["performance_ranking_authorized"])
