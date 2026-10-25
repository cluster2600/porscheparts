"""Synthetic boundary tests; optional native checks are explicitly skipped when absent."""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import shlex
import subprocess
import time
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "benchmarks/free-tools"
# Keep standalone CLI modules out of other repository tests' import namespaces.
prior_path = sys.path[:]
sys.path.insert(0, str(TOOLS))
import ft_common as common
import ft_geometry as geometry
from ft_beam_solver import solve


def tool_module(name):
    spec = importlib.util.spec_from_file_location("ft_" + name, TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pilot, knowledge, storage, cloudcompare, salome_worker, studies = [
    tool_module(name)
    for name in (
        "pilot",
        "knowledge",
        "storage",
        "cloudcompare",
        "salome_worker",
        "studies",
    )
]
sys.path[:] = prior_path
native_container = tool_module("native_container")


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_nonfinite_and_boolean_numbers_rejected(self):
        for value in [True, False, float("nan"), float("inf"), "1"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.finite(value)

    def test_nonfinite_json_rejected(self):
        p = self.root / "bad.json"
        p.write_text('{"x":NaN}')
        with self.assertRaises(ValueError):
            common.load(p)

    def test_output_is_never_overwritten(self):
        p = common.new_directory(self.root / "result")
        (p / "kept").write_text("original")
        with self.assertRaises(ValueError):
            common.new_directory(p)
        self.assertEqual((p / "kept").read_text(), "original")

    def test_symlink_and_escape_artifacts_rejected(self):
        (self.root / "file").write_text("data")
        (self.root / "link").symlink_to(self.root / "file")
        for name in ["link", "../file", str(self.root / "file")]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                common.source_path(self.root, name)

    def test_hash_mismatch_rejected(self):
        (self.root / "data").write_text("changed")
        with self.assertRaises(ValueError):
            common.verify_inputs(
                {"inputs": [{"path": "data", "sha256": "0" * 64}]}, self.root
            )

    def test_timeout_kills_owned_child(self):
        marker = self.root / "escaped"
        child = f"import time,pathlib; time.sleep(0.3); pathlib.Path({str(marker)!r}).write_text('bad')"
        code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(5)"
        with self.assertRaises(TimeoutError):
            common.checked([sys.executable, "-c", code], self.root, 0.15)
        time.sleep(0.4)
        self.assertFalse(marker.exists())

    def test_missing_output_is_not_success(self):
        execution = common.checked([sys.executable, "-c", "pass"], self.root, 2)
        self.assertEqual(execution["exit_status"], 0)
        with self.assertRaises(FileNotFoundError):
            common.sha256(self.root / "missing")

    def test_carrier_registered_inputs_keep_optimization_blocked(self):
        manifest = common.load(TOOLS / "baseline.json")
        # A full checkout is required for this integration check, not invented inputs.
        try:
            common.verify_inputs(manifest, pilot.ROOT)
        except (ValueError, FileNotFoundError):
            self.skipTest("registered carrier artifacts unavailable in sparse checkout")
        result = pilot.replay(TOOLS / "baseline.json", pilot.ROOT, self.root / "replay")
        self.assertEqual(result["status"], "blocked_engineering")
        self.assertIs(result["checks"]["optimization_enabled"], False)
        self.assertIn(
            "carrier_mesh_convergence_not_demonstrated", result["checks"]["blockers"]
        )

    def test_caller_cannot_authorize_modified_interface(self):
        manifest = common.load(TOOLS / "baseline.json")
        manifest["inputs"] = []
        common.write(self.root / "manifest.json", manifest)
        with self.assertRaises(ValueError):
            pilot.replay(self.root / "manifest.json", self.root, self.root / "result")

    def test_documentary_cases_and_index_staleness(self):
        database = knowledge.build(TOOLS / "corpus.json", self.root / "index")
        result = knowledge.evaluate(
            database, TOOLS / "corpus.json", TOOLS / "retrieval-cases.json"
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["passed"],
            {"reference": 10, "unknown": 10, "conflict": 5, "hostile": 5},
        )
        changed = self.root / "changed.json"
        changed.write_text((TOOLS / "corpus.json").read_text() + " ")
        with self.assertRaises(ValueError):
            knowledge.context(database, changed, "99311502153")

    def test_query_syntax_and_reference_normalization(self):
        database = knowledge.build(TOOLS / "corpus.json", self.root / "index")
        for query in [
            "993 115 021 53",
            "993.115.021.53",
            "993-115-021-53",
            "99311502153",
        ]:
            self.assertIn(
                "carrier",
                [
                    r["id"]
                    for r in knowledge.context(database, TOOLS / "corpus.json", query)[
                        "sources"
                    ]
                ],
            )
        self.assertIs(
            knowledge.context(database, TOOLS / "corpus.json", '" OR 1=1 --')[
                "engineering_authorized"
            ],
            False,
        )

    def test_hostile_documents_are_data_only(self):
        database = knowledge.build(TOOLS / "corpus.json", self.root / "index")
        with patch.object(knowledge, "checked") as execution:
            brief = knowledge.context(database, TOOLS / "corpus.json", "hostilefixture")
            text = knowledge.prompt(brief)
        execution.assert_not_called()
        self.assertIn("untrusted reference data", text)
        self.assertIn("touch /tmp/free-tools-injection", text)
        self.assertIs(brief["engineering_authorized"], False)

    def test_unauthorized_snapshot_rejected(self):
        common.write(self.root / "snapshot.json", {"documents": []})
        with self.assertRaises(ValueError):
            knowledge.build(self.root / "snapshot.json", self.root / "index")

    def test_catalogue_snapshot_excludes_unallowlisted_fields_and_synthetic_attacks(
        self,
    ):
        if not (pilot.ROOT / pilot.PART).is_file():
            self.skipTest("carrier catalogue absent")
        root = self.root / "repository"
        for relative in [pilot.PART, pilot.CONVERGENCE]:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pilot.ROOT / relative, destination)
        record = common.load(root / pilot.PART)
        record["private_extra"] = "DO_NOT_IMPORT"
        (root / pilot.PART).write_text(json.dumps(record))
        data = knowledge.snapshot(root, self.root / "production.json")
        self.assertNotIn("DO_NOT_IMPORT", json.dumps(data))
        self.assertFalse(
            any(row["source"].startswith("synthetic:") for row in data["documents"])
        )
        self.assertIn("catalogue-record", [row["id"] for row in data["documents"]])
        self.assertEqual(data["porschefanatics_export"], "not_supplied")

    def test_model_draft_cannot_invent_citations_or_drop_unknowns(self):
        brief = {"sources": [{"id": "interfaces"}]}
        valid = {
            "answer": "Interfaces remain unmeasured.",
            "source_ids": ["interfaces"],
            "unknowns": ["hole centres"],
        }
        self.assertTrue(knowledge.validate_answer(json.dumps(valid), brief)["passed"])
        for value in [
            "not JSON",
            json.dumps(dict(valid, source_ids=["invented"])),
            json.dumps(dict(valid, unknowns=[])),
            json.dumps(dict(valid, engineering_authorized=True)),
        ]:
            self.assertFalse(knowledge.validate_answer(value, brief)["passed"])

    def test_porschefanatics_export_only_imports_authorized_identity_fields(self):
        site = self.root / "site"
        (site / "data").mkdir(parents=True)
        common.write(
            site / "data/oem-parts.json",
            {
                "oemParts": [
                    {
                        "id": "993-115-021-53",
                        "oemReference": "993 115 021 53",
                        "englishName": "Engine carrier",
                        "generationId": "993",
                        "notes": "NOT_FOR_EXPORT",
                        "petEvidence": "NOT_FOR_EXPORT",
                    }
                ]
            },
        )
        result = knowledge.export_porschefanatics(site, self.root / "export.json")
        self.assertNotIn("NOT_FOR_EXPORT", json.dumps(result))
        self.assertEqual(
            result["documents"][0]["scope"], "catalogue_identity_only_not_measurement"
        )
        self.assertIn("993 115 021 53", result["documents"][0]["text"])

    def test_native_ssh_transport_is_strict_and_never_uses_dvc_ssh(self):
        with patch.object(
            storage, "checked", return_value={"stdout": "", "exit_status": 0}
        ) as command:
            storage.ssh_transfer(
                "ssh://operator@kali.example/home/operator/private-store",
                self.root,
                True,
                self.root,
            )
        argv = command.call_args_list[0].args[0]
        self.assertIn("StrictHostKeyChecking=yes", argv)
        self.assertIn("BatchMode=yes", argv)
        self.assertIn("ForwardAgent=no", argv)
        with self.assertRaises(ValueError):
            storage.ssh_transfer(
                "ssh://user:password@host/data", self.root, True, self.root
            )

    def test_ssh_path_validation_survives_optimized_python(self):
        target = self.root / "real"
        target.mkdir()
        link = self.root / "link"
        link.symlink_to(target, target_is_directory=True)
        with patch.object(
            storage, "checked", return_value={"stdout": "", "exit_status": 0}
        ) as command:
            storage.ssh_transfer(
                "ssh://operator@host" + str(link), self.root, True, self.root
            )
        remote = shlex.split(command.call_args_list[0].args[0][-1])
        result = subprocess.run(
            [sys.executable, "-O", *remote[1:]], capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical store path required", result.stderr)

    def test_container_identity_is_outside_mount_and_acceptance_requires_absence(self):
        identifier = "a" * 64

        def execute(argv, cwd, *args):
            if argv[1:3] == ["image", "inspect"]:
                return {
                    "stdout": json.dumps(
                        [
                            {
                                "Architecture": "amd64",
                                "Os": "linux",
                                "Id": "sha256:" + "b" * 64,
                            }
                        ]
                    )
                }
            cid = Path(argv[argv.index("--cidfile") + 1])
            self.assertFalse(cid.is_relative_to(Path(cwd)))
            cid.write_text(identifier)
            result = Path(cwd) / "result"
            result.mkdir()
            common.write(result / "receipt.json", {"status": "passed"})
            return {"stdout": "", "exit_status": 0}

        for remains in [False, True]:
            output = self.root / ("remains" if remains else "removed")

            def docker(argv, **kwargs):
                return subprocess.CompletedProcess(
                    argv, 0, identifier if remains and argv[1] == "ps" else "", ""
                )

            with patch.object(
                native_container, "checked", side_effect=execute
            ), patch.object(native_container.subprocess, "run", side_effect=docker):
                if remains:
                    with self.assertRaises(RuntimeError):
                        native_container.run("cloudcompare", "test-image", output)
                    self.assertFalse((output / "receipt.json").exists())
                else:
                    report = native_container.run("cloudcompare", "test-image", output)
                    self.assertTrue(
                        report["checks"]["owned_container_absence_verified"]
                    )

    def test_private_dvc_workspace_cannot_live_in_checkout(self):
        with self.assertRaises(ValueError):
            storage.private_root(TOOLS / "private-data")
        with self.assertRaises(ValueError):
            storage.store_location(self.root, self.root / "workspace")

    def test_password_remote_rejected(self):
        with self.assertRaises(ValueError):
            storage.store_location("ssh://user:password@host/data", self.root)

    def test_rigid_transform_rejects_scale_reflection_and_nan(self):
        for matrix in [
            [[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            [[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            [[1, 0, 0, float("nan")], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        ]:
            with self.assertRaises(ValueError):
                geometry.rigid_points([[0, 0, 0]], matrix)
        self.assertEqual(
            geometry.rigid_points(
                [[0, 0, 3]], [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -3], [0, 0, 0, 1]]
            ),
            [[0, 0, 0]],
        )

    def test_cloudcompare_bad_units_and_points_fail_before_execution(self):
        cloud = self.root / "points.xyz"
        cloud.write_text("0 0 nan\n")
        config = self.root / "case.json"
        common.write(config, {"units": "mm"})
        with patch.object(cloudcompare, "checked") as run, self.assertRaises(
            ValueError
        ):
            cloudcompare.compare(
                cloud, self.root / "mesh.obj", config, self.root / "result"
            )
        run.assert_not_called()
        config.write_text('{"units":"m"}')
        with self.assertRaises(ValueError):
            cloudcompare.compare(
                cloud, self.root / "mesh.obj", config, self.root / "result"
            )

    def test_open_shell_rejected_and_bore_fixture_closed(self):
        for name in ["cube", "bore"]:
            points, faces, _ = salome_worker.fixture(name)
            geometry.closed_surface(points, faces)
            with self.assertRaises(ValueError):
                geometry.closed_surface(points, faces[:-1])

    def test_inverted_tet_rejected_and_calculix_roundtrip(self):
        points = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        faces = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
        self.assertTrue(
            geometry.verify_tets(points, [[0, 1, 2, 3]], points, faces)[
                "exact_boundary_identity"
            ]
        )
        with self.assertRaises(ValueError):
            geometry.verify_tets(points, [[1, 0, 2, 3]], points, faces)
        with self.assertRaises(ValueError):
            geometry.verify_tets(points, [[0, 1, 2, 3]], points, faces[:-1])
        groups = {"support": [0, 1, 2]}
        salome_worker.write_inp(self.root / "mesh.inp", points, [[0, 1, 2, 3]], groups)
        self.assertEqual(
            salome_worker.read_inp(self.root / "mesh.inp"),
            (points, [[0, 1, 2, 3]], groups),
        )

    def test_failed_or_nonfinite_sensitivity_sample_not_discarded(self):
        with self.assertRaises(ValueError):
            studies.evaluate_samples([[0, 1]], lambda x: float("nan"))

        def failed(_):
            raise RuntimeError("solver failed")

        with self.assertRaises(RuntimeError):
            studies.evaluate_samples([[0, 1]], failed)
        with self.assertRaises(ValueError):
            studies.evaluate_samples([[True, 1]], lambda x: 0.0)

    def test_beam_units_and_nonfinite_rejected(self):
        data = {
            "length": 1.0,
            "width": 0.05,
            "height": 0.02,
            "force": 10.0,
            "modulus": 70e9,
            "density": 2700.0,
            "units": {"length": "m", "force": "N", "modulus": "Pa", "density": "kg/m3"},
        }
        self.assertGreater(solve(data)["mass"], 0)
        with self.assertRaises(ValueError):
            solve(dict(data, height=float("nan")))
        with self.assertRaises(ValueError):
            solve(dict(data, units={"length": "mm"}))


@unittest.skipUnless(
    importlib.util.find_spec("dvc"), "DVC native dependency unavailable"
)
class NativeDVC(unittest.TestCase):
    setUp = Boundaries.setUp

    def test_fresh_restore_two_independent_local_stores_and_corruption(self):
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_text("synthetic artifact")
        manifest = {
            "inputs": [{"path": "data", "sha256": common.sha256(source / "data")}]
        }
        common.write(self.root / "manifest.json", manifest)
        metadata = self.root / "metadata"
        storage.archive(
            self.root / "manifest.json", source, metadata, self.root / "store-a"
        )
        storage.replicate(metadata, self.root / "store-b")
        for name in ["a", "b"]:
            result = storage.restore(
                metadata, self.root / f"restore-{name}", self.root / f"store-{name}"
            )
            self.assertEqual(result["status"], "restored_sha256_verified")
        objects = [p for p in (self.root / "store-b").rglob("*") if p.is_file()]
        self.assertTrue(objects)
        for p in objects:
            p.chmod(0o600)
            p.write_bytes(b"corrupted")
        with self.assertRaises((ValueError, RuntimeError)):
            storage.restore(
                metadata, self.root / "corrupt-restore", self.root / "store-b"
            )

    def test_missing_and_interrupted_transfer_keep_no_success_receipt(self):
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_text("synthetic")
        common.write(
            self.root / "manifest.json",
            {"inputs": [{"path": "data", "sha256": common.sha256(source / "data")}]},
        )
        metadata = self.root / "metadata"
        storage.archive(
            self.root / "manifest.json", source, metadata, self.root / "store"
        )
        with self.assertRaises(RuntimeError):
            storage.restore(metadata, self.root / "missing", self.root / "empty-store")
        self.assertFalse((self.root / "missing/restore-receipt.json").exists())
        with patch.object(
            storage, "dvc", side_effect=TimeoutError("simulated transfer interruption")
        ), self.assertRaises(TimeoutError):
            storage.restore(metadata, self.root / "interrupted", self.root / "store")
        self.assertFalse((self.root / "interrupted/restore-receipt.json").exists())


@unittest.skipUnless(
    importlib.util.find_spec("openturns") and importlib.util.find_spec("openmdao"),
    "native study dependencies unavailable",
)
class NativeStudies(unittest.TestCase):
    def test_analytical_controls_and_infeasible_case(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(
                studies.sensitivity(root / "sensitivity")["status"], "passed"
            )
            self.assertEqual(
                studies.optimization(root / "optimization")["status"], "passed"
            )
            with self.assertRaises(ValueError):
                studies.optimization(root / "infeasible", deflection_limit=1e-8)


@unittest.skipUnless(
    shutil.which("CloudCompare"), "CloudCompare native executable unavailable"
)
class NativeCloudCompare(unittest.TestCase):
    def test_analytic_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            cloudcompare.controls(Path(temp) / "native")


if __name__ == "__main__":
    unittest.main()
