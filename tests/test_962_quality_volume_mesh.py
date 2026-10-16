"""Admission cannot be inferred from a status label or stale evidence hashes."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("quality_volume", SOURCE / "mesh_quality_head.py")
mesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh)


class AdmissionGuard(unittest.TestCase):
    def test_pending_nonbool_missing_or_drifted_admission_never_creates_output_or_launches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); candidate = root / "candidate.bin"; candidate.write_bytes(b"bound candidate")
            evidence = root / "evidence.json"; evidence.write_text("completed independent evidence")
            admission = root / "admission.json"; output = root / "never-created"
            base = dict(candidate_sha256=mesh.sha(candidate), length_unit="mm",
                candidate_volume_mm3=mesh.CANDIDATE_VOLUME, numerical_surface_admitted=True,
                gates={key: True for key in mesh.GATES}, input_hashes={"evidence.json": mesh.sha(evidence)})
            with mock.patch.object(mesh, "ROOT", root), mock.patch.object(mesh, "CANDIDATE", candidate), \
                    mock.patch.object(mesh, "CANDIDATE_SHA", mesh.sha(candidate)), \
                    mock.patch.object(mesh, "OUTPUT", output), mock.patch.object(mesh.subprocess, "Popen") as launch:
                admission.write_text(json.dumps(base))
                self.assertTrue(mesh.require_admission(admission, mesh.sha(admission))["numerical_surface_admitted"])
                for value in [False, 1, "true", None]:
                    row = {**base, "gates": {**base["gates"], "distance": value}}
                    admission.write_text(json.dumps(row))
                    args = argparse.Namespace(admission=admission, admission_sha256=mesh.sha(admission), output=output)
                    with self.subTest(value=value), self.assertRaises(ValueError): mesh.run(args)
                    self.assertFalse(output.exists()); launch.assert_not_called()
                row = {**base, "gates": {key: True for key in mesh.GATES if key != "features"}}
                admission.write_text(json.dumps(row))
                with self.assertRaises(ValueError):
                    mesh.run(argparse.Namespace(admission=admission, admission_sha256=mesh.sha(admission), output=output))
                admission.write_text(json.dumps(base)); evidence.write_text("changed evidence")
                with self.assertRaisesRegex(ValueError, "evidence changed"):
                    mesh.run(argparse.Namespace(admission=admission, admission_sha256=mesh.sha(admission), output=output))
                self.assertFalse(output.exists()); launch.assert_not_called()
                self.assertEqual(candidate.read_bytes(), b"bound candidate")

    def test_completed_worker_missing_mesh_or_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); admission = root / "admission.json"; admission.write_text("bound receipt")
            for missing in ["mesh", "digest"]:
                output = root / missing
                process = mock.Mock(pid=12345, returncode=0)
                process.poll.return_value = 0
                def completed_worker(*args, **kwargs):
                    report = dict(status="completed_geometric_volume_quality_only",
                                  qualification=dict(geometric_volume_gate_passed=True))
                    if missing == "mesh": report["mesh_sha256"] = "a" * 64
                    else: (output / "head-volume.msh").write_bytes(b"nonempty mesh")
                    (output / "worker-report.json").write_text(json.dumps(report))
                    return process
                with self.subTest(missing=missing), mock.patch.object(mesh, "ROOT", root), \
                        mock.patch.object(mesh, "OUTPUT", output), \
                        mock.patch.object(mesh, "source_files", return_value=[]), \
                        mock.patch.object(mesh, "require_admission"), \
                        mock.patch.object(mesh.subprocess, "Popen", side_effect=completed_worker), \
                        mock.patch.object(mesh.threading, "Timer"):
                    result = mesh.run(argparse.Namespace(admission=admission,
                        admission_sha256=mesh.sha(admission), output=output))
                    self.assertEqual(result, 2)
                    self.assertFalse(json.loads((output / "receipt.json").read_text())["geometric_volume_gate_passed"])

    def test_mesh_identity_requires_nonempty_regular_file_and_valid_exact_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mesh.msh"; path.write_bytes(b"mesh")
            digest = mesh.sha(path)
            self.assertTrue(mesh.matching_mesh(path, digest))
            for bad in [None, "", digest.upper(), "a" * 64]:
                self.assertFalse(mesh.matching_mesh(path, bad))
            link = path.with_name("link.msh"); link.symlink_to(path)
            self.assertFalse(mesh.matching_mesh(link, digest))
            self.assertFalse(mesh.matching_mesh(path.parent, digest))
            path.write_bytes(b"")
            self.assertFalse(mesh.matching_mesh(path, mesh.sha(path)))

    def test_watchdog_start_failure_kills_and_reaps_spawned_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); admission = root / "admission.json"; admission.write_text("bound receipt")
            output = root / "output"
            process = mock.Mock(pid=12345, returncode=None); process.poll.return_value = None
            timer = mock.Mock(); timer.start.side_effect = RuntimeError("watchdog startup failed")
            with mock.patch.object(mesh, "ROOT", root), mock.patch.object(mesh, "OUTPUT", output), \
                    mock.patch.object(mesh, "source_files", return_value=[]), \
                    mock.patch.object(mesh, "require_admission"), \
                    mock.patch.object(mesh.subprocess, "Popen", return_value=process), \
                    mock.patch.object(mesh.threading, "Timer", return_value=timer), \
                    mock.patch.object(mesh.os, "killpg") as kill:
                with self.assertRaisesRegex(RuntimeError, "watchdog startup failed"):
                    mesh.run(argparse.Namespace(admission=admission,
                        admission_sha256=mesh.sha(admission), output=output))
                kill.assert_called_once_with(process.pid, mesh.signal.SIGKILL)
                process.wait.assert_called_once_with(); timer.cancel.assert_called_once_with()


class TetraFaceOrientation(unittest.TestCase):
    def test_duplicate_positive_interior_tets_fail_despite_matching_exterior_and_volume(self):
        np = mesh.np
        outer = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        points = np.concatenate([outer, .2 + .001 * outer])
        cells = np.array([[0, 1, 2, 3], [4, 5, 6, 7], [4, 5, 6, 7]])
        boundary = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
        self.assertTrue(mesh.tetra_boundary(cells, boundary)["exact_oriented_tetra_boundary"])
        volumes = mesh.tetra_volumes(points, cells)
        self.assertTrue(np.all(volumes > 0))
        self.assertLess(abs(volumes.sum() / (1/6) - 1), 1e-6)
        with self.assertRaisesRegex(ValueError, "opposite orientations"):
            mesh.internal_face_orientation(cells)

    def test_oppositely_oriented_shared_face_passes(self):
        cells = mesh.np.array([[0, 1, 2, 3], [0, 2, 1, 4]])
        report = mesh.internal_face_orientation(cells)
        self.assertTrue(report["exact_internal_orientation_balance"])
        self.assertEqual(report["internal_faces"], 1)


if __name__ == "__main__":
    unittest.main()
