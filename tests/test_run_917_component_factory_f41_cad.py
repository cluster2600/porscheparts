#!/usr/bin/env python3
"""Offline tests for the fail-closed F41 paid-run supervisor."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "deploy/openbao/run-917-component-factory-f41-cad"
RESULT_TESTS = ROOT / "tests/test_917_component_factory_f41_cad_results.py"
SOURCE_REVISION = "a" * 40
EXPECTED_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:" + "b" * 64
)
JOB_ID = "f41-cad-supervisor-test"
ALLOWED_BUNDLE_FILES = (
    "REMOTE_JOB.md",
    "containers/simready-preflight/convert.py",
    "docs/917_COMPONENT_FACTORY_F41.md",
    "twins/reference-917-engine/component-factory-f41.json",
    "twins/reference-917-engine/rotating-assembly-cad-f35.json",
    "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
    "twins/reference-917-engine/source/execute_component_factory_f41.py",
    "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
    "twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh",
    "twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh",
)
EXECUTABLE_BUNDLE_FILES = frozenset(
    {
        "twins/reference-917-engine/source/execute_component_factory_f41.py",
        "twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh",
        "twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh",
    }
)
RUNTIME_IMAGES = [
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
    "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
    "41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe",
]


def load_result_test_module():
    spec = importlib.util.spec_from_file_location("existing_f41_result_tests", RESULT_TESTS)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load result archive test helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F41SupervisorTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="f41-supervisor-test-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        self.bin = self.root / "bin"
        self.bin.mkdir(mode=0o700)
        self.output = self.root / "run-output"
        self.events = self.root / "events.log"
        self.identity = self.root / "id_vastai"
        self.identity.write_text("fixture-not-a-real-private-key\n", encoding="utf-8")
        self.identity.chmod(0o600)
        self.bundle = self.write_bundle()
        self.bundle_sha256 = self.digest(self.bundle)
        self.result_archive = self.write_result_archive()
        self.result_listing = self.root / "result.list.txt"
        self.result_listing.write_text(f"{JOB_ID}/\n", encoding="utf-8")
        self.write_fakes()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def write_bundle(self) -> Path:
        bundle = self.root / "917-component-factory-f41-public.tar.gz"
        payloads = {
            name: (f"public fixture for {name}\n").encode("utf-8")
            for name in ALLOWED_BUNDLE_FILES
        }
        entries = []
        for name in sorted(payloads):
            mode = "0755" if name in EXECUTABLE_BUNDLE_FILES else "0644"
            entries.append(
                {
                    "mode": mode,
                    "path": name,
                    "sha256": hashlib.sha256(payloads[name]).hexdigest(),
                    "size_bytes": len(payloads[name]),
                }
            )
        manifest = {
            "all_payload_files_utf8_text": True,
            "archive_member_count": len(payloads) + 1,
            "binary_payload_included": False,
            "bundle_root": "917-component-factory-f41",
            "file_count": len(payloads),
            "files": entries,
            "newly_generated_geometry_included": False,
            "phase": "F41",
            "private_absolute_path_included": False,
            "public_remote_refs": ["refs/remotes/origin/main"],
            "raw_scan_included": False,
            "required_runtime_images": RUNTIME_IMAGES,
            "schema_version": "1.1.0",
            "secret_included": False,
            "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
            "source_revision": SOURCE_REVISION,
            "status": "public_transfer_bundle_file_manifest",
        }
        payloads["BUNDLE-MANIFEST.json"] = (
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        with tarfile.open(bundle, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            for relative, payload in sorted(payloads.items()):
                member = tarfile.TarInfo(f"917-component-factory-f41/{relative}")
                member.size = len(payload)
                member.mode = 0o755 if relative in EXECUTABLE_BUNDLE_FILES else 0o644
                member.mtime = 0
                import io

                archive.addfile(member, io.BytesIO(payload))
        return bundle

    def write_result_archive(self) -> Path:
        module = load_result_test_module()
        module.ComponentFactoryF41CadResultsTest.setUpClass()
        helper = module.ComponentFactoryF41CadResultsTest(
            "test_valid_archive_extracts_and_verifies_exact_evidence"
        )
        helper.validator = module.ComponentFactoryF41CadResultsTest.validator
        helper.job_id = JOB_ID
        helper.root = self.root
        return helper.write_archive(helper.valid_payloads())

    def executable(self, name: str, source: str) -> Path:
        path = self.bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)
        return path

    def write_fakes(self) -> None:
        self.fake_git = self.executable(
            "fake-git",
            r'''
            #!/usr/bin/env python3
            import os
            import sys
            if "rev-parse" in sys.argv:
                print(os.environ["FAKE_SOURCE_REVISION"])
                raise SystemExit(0)
            if "status" in sys.argv:
                raise SystemExit(0)
            raise SystemExit(2)
            ''',
        )
        self.fake_wrapper = self.executable(
            "fake-wrapper",
            r'''
            #!/usr/bin/env python3
            import json
            import os
            from pathlib import Path
            import sys

            state_path = Path(os.environ["FAKE_STATE"])
            events = Path(os.environ["FAKE_EVENTS"])
            state = json.loads(state_path.read_text()) if state_path.exists() else {"created": False}
            operation = sys.argv[1]
            with events.open("a", encoding="utf-8") as stream:
                stream.write(f"wrapper:{operation}\n")
            instance_id = 4242
            label = state.get(
                "label",
                "3dprinting993-component-factory-f41-cad-0123456789abcdefabcd",
            )
            image = os.environ["FAKE_EXPECTED_IMAGE"]
            known = Path(os.environ["HOME"]) / ".cache/openbao-vastai/known-hosts" / f"f41-{instance_id}"

            def safe_instance():
                return {
                    "id": instance_id,
                    "image": state.get("image", image),
                    "label": label,
                    "ssh_host": "ssh7.vast.ai",
                    "ssh_port": "2222",
                    "status": "running",
                }

            if operation == "instances":
                malformed = int(state.get("malformed_inventories", 0))
                if state.get("created") and malformed > 0:
                    state["malformed_inventories"] = malformed - 1
                    state_path.write_text(json.dumps(state))
                    print(json.dumps([{"id": str(instance_id), "label": None}]))
                    raise SystemExit(0)
                transient = int(state.get("transient_empty_inventories", 0))
                if state.get("created") and transient > 0:
                    state["transient_empty_inventories"] = transient - 1
                    state_path.write_text(json.dumps(state))
                    print("[]")
                    raise SystemExit(0)
                print(json.dumps([safe_instance()] if state.get("created") else []))
                raise SystemExit(0)
            if operation == "launch-component-factory-f41":
                if len(sys.argv) != 5 or sys.argv[3] != "--attempt-label":
                    print("supervisor label missing", file=sys.stderr)
                    raise SystemExit(65)
                label = sys.argv[4]
                state["created"] = True
                state["label"] = label
                state["transient_empty_inventories"] = int(
                    os.environ.get("FAKE_TRANSIENT_EMPTY_INVENTORIES", "0")
                )
                state_path.write_text(json.dumps(state))
                known.parent.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                known.parent.parent.chmod(0o700)
                known.parent.mkdir(mode=0o700, exist_ok=True)
                known.parent.chmod(0o700)
                known.write_text(f"f41-{instance_id} ssh-ed25519 AAAATEST\n")
                known.chmod(0o600)
                mode = os.environ.get("FAKE_LAUNCH_MODE", "success")
                if mode.startswith("child-cleanup-"):
                    variant = mode.removeprefix("child-cleanup-")
                    state["created"] = variant.endswith("-live")
                    state_path.write_text(json.dumps(state))
                    receipt = {
                        "schema_version": "1.0.0",
                        "status": "destroyed_verified_absent",
                        "instance_id": instance_id,
                        "label": label,
                        "image": image,
                        "delete_acknowledged": True,
                        "paginated_absence_verified": True,
                    }
                    if variant == "wrong-label-absent":
                        receipt["label"] = (
                            "3dprinting993-component-factory-f41-cad-"
                            "fedcba9876543210fedc"
                        )
                    elif variant == "wrong-image-live":
                        receipt["image"] = (
                            "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
                            + "c" * 64
                        )
                    elif variant == "wrong-id-live":
                        receipt["instance_id"] = instance_id + 1
                    elif variant == "false-proof-live":
                        receipt["delete_acknowledged"] = False
                    payload = (
                        "OPENBAO_VASTAI_F41_CLEANUP "
                        + json.dumps(receipt, sort_keys=True, separators=(",", ":"))
                    )
                    print(payload, file=sys.stderr)
                    if variant == "duplicate-live":
                        print(payload, file=sys.stderr)
                    raise SystemExit(9)
                if mode == "wrong-image":
                    state["image"] = (
                        "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
                        + "c" * 64
                    )
                    state_path.write_text(json.dumps(state))
                if mode == "nonzero-noidentity":
                    print("synthetic launch interruption", file=sys.stderr)
                    raise SystemExit(9)
                if mode == "nonzero-label-stderr":
                    print(f"synthetic launch interruption for {label}", file=sys.stderr)
                    raise SystemExit(9)
                report = {
                    "instance_id": instance_id,
                    "image": state.get("image", image),
                    "label": label,
                    "known_hosts_path": str(known),
                    "host_key_alias": f"f41-{instance_id}",
                    "offer_contract_verified": True,
                    "singleton_preflight_verified": True,
                    "singleton_verified": True,
                    "contract_verified": True,
                    "running_state_verified": True,
                    "ssh_batch_mode_verified": True,
                    "image_transport_smoke_verified": True,
                    "f41_component_factory_executed": False,
                    "physical_claims_validated": False,
                    "manufacturing_authorized": False,
                }
                if mode == "invalid-gate":
                    report["contract_verified"] = False
                print(json.dumps(report))
                raise SystemExit(9 if mode == "nonzero-json" else 0)
            if operation == "show":
                if not state.get("created"):
                    raise SystemExit(4)
                state["show_calls"] = int(state.get("show_calls", 0)) + 1
                state_path.write_text(json.dumps(state))
                fail_on_call = int(os.environ.get("FAKE_SHOW_FAIL_ON_CALL", "0"))
                if fail_on_call == state["show_calls"]:
                    state["transient_empty_inventories"] = int(
                        os.environ.get(
                            "FAKE_SHOW_FAILURE_TRANSIENT_EMPTY_INVENTORIES", "0"
                        )
                    )
                    state_path.write_text(json.dumps(state))
                    raise SystemExit(4)
                print(json.dumps(safe_instance()))
                raise SystemExit(0)
            if operation == "destroy":
                if not known.is_file():
                    print("known_hosts missing before destroy", file=sys.stderr)
                    raise SystemExit(5)
                if (Path(os.environ["FAKE_OUTPUT_ROOT"]) / "validated").exists():
                    print("validator ran before destroy", file=sys.stderr)
                    raise SystemExit(6)
                if os.environ.get("FAKE_DESTROY_FAIL") == "1":
                    state["transient_empty_inventories"] = int(
                        os.environ.get(
                            "FAKE_DESTROY_FAIL_TRANSIENT_EMPTY_INVENTORIES", "0"
                        )
                    )
                    state_path.write_text(json.dumps(state))
                    print("synthetic destroy outage", file=sys.stderr)
                    raise SystemExit(7)
                state["destroy_called"] = True
                if os.environ.get("FAKE_DESTROY_LIES") == "1":
                    state["malformed_inventories"] = int(
                        os.environ.get("FAKE_MALFORMED_POST_DESTROY_INVENTORIES", "0")
                    )
                else:
                    state["created"] = False
                state_path.write_text(json.dumps(state))
                print(json.dumps({"instance_id": instance_id, "destroyed": True, "verified_absent": True}))
                raise SystemExit(0)
            raise SystemExit(64)
            ''',
        )
        self.fake_ssh = self.executable(
            "fake-ssh",
            r'''
            #!/usr/bin/env python3
            import hashlib
            import json
            import os
            from pathlib import Path
            import sys
            import time
            argv = sys.argv[1:]
            joined = " ".join(argv)
            required = (
                "StrictHostKeyChecking=yes",
                "UpdateHostKeys=no",
                "HashKnownHosts=no",
                "HostKeyAlias=f41-4242",
                "GlobalKnownHostsFile=/dev/null",
                "UserKnownHostsFile=",
                "BatchMode=yes",
                "IdentitiesOnly=yes",
            )
            if any(value not in joined for value in required) or "accept-new" in joined:
                print("unsafe ssh options", file=sys.stderr)
                raise SystemExit(80)
            command = argv[-1]
            with Path(os.environ["FAKE_EVENTS"]).open("a", encoding="utf-8") as stream:
                stream.write(f"ssh:{command.splitlines()[0]}\n")
            fail_match = os.environ.get("FAKE_FAIL_SSH_MATCH", "")
            if fail_match and fail_match in command:
                raise SystemExit(81)
            noisy_match = os.environ.get("FAKE_NOISY_SSH_MATCH", "")
            if noisy_match and noisy_match in command:
                child = os.fork()
                if child == 0:
                    time.sleep(0.2)
                    sys.stdout.buffer.write(b"x" * (3 * 1024 * 1024))
                    sys.stdout.buffer.flush()
                    time.sleep(20)
                    os._exit(0)
                raise SystemExit(0)
            if command.startswith("917-cad-stage-job "):
                print(json.dumps({
                    "status": "public_archive_staged_cad_execution_not_started",
                    "job_id": os.environ["FAKE_JOB_ID"],
                    "archive_sha256": os.environ["FAKE_BUNDLE_SHA"],
                    "archive_bytes": int(os.environ["FAKE_BUNDLE_SIZE"]),
                    "source_revision": os.environ["FAKE_SOURCE_REVISION"],
                    "regular_payloads_utf8_text_only": True,
                    "private_assets_included": False,
                    "secret_material_included": False,
                    "target_uid": 9178,
                    "target_gid": 9178,
                    "cad_started": False,
                    "physical_claims_validated": False,
                    "manufacturing_authorized": False,
                }))
            elif "917-cad-run-job" in command:
                if "/usr/bin/timeout --signal=TERM --kill-after=60s 45m" not in command:
                    raise SystemExit(82)
                print(json.dumps({
                    "status": "passed_six_hash_bound_F35_seed_families_generated_not_released",
                    "planned_family_count": 138,
                    "generateable_family_count": 6,
                    "generated_family_count": 6,
                    "blocked_family_count": 132,
                    "generated_format_counts": {"STEP": 6, "STL": 6, "3MF": 6, "USD": 0},
                    "paid_instance_launched": False,
                }))
            elif "/usr/bin/tar --version" in command:
                expected_exclude = "--exclude='" + os.environ["FAKE_JOB_ID"] + "/.runtime'"
                if expected_exclude not in command:
                    raise SystemExit(83)
                archive = Path(os.environ["FAKE_RESULT_ARCHIVE"])
                listing = Path(os.environ["FAKE_RESULT_LISTING"])
                def digest(path):
                    return hashlib.sha256(path.read_bytes()).hexdigest()
                print(json.dumps({
                    "archive_sha256": digest(archive),
                    "archive_size_bytes": archive.stat().st_size,
                    "gnu_tar": True,
                    "listing_sha256": digest(listing),
                    "listing_size_bytes": listing.stat().st_size,
                    "runtime_excluded": True,
                }))
            raise SystemExit(0)
            ''',
        )
        self.fake_scp = self.executable(
            "fake-scp",
            r'''
            #!/usr/bin/env python3
            import os
            from pathlib import Path
            import shutil
            import sys
            argv = sys.argv[1:]
            joined = " ".join(argv)
            required = (
                "StrictHostKeyChecking=yes",
                "UpdateHostKeys=no",
                "HashKnownHosts=no",
                "HostKeyAlias=f41-4242",
                "GlobalKnownHostsFile=/dev/null",
                "UserKnownHostsFile=",
            )
            if any(value not in joined for value in required) or "accept-new" in joined:
                raise SystemExit(80)
            source, destination = argv[-2:]
            with Path(os.environ["FAKE_EVENTS"]).open("a", encoding="utf-8") as stream:
                stream.write(f"scp:{source}\n")
            if source.startswith("root@") and source.endswith(".tar.gz"):
                shutil.copyfile(os.environ["FAKE_RESULT_ARCHIVE"], destination)
            elif source.startswith("root@") and source.endswith(".tar.list.txt"):
                shutil.copyfile(os.environ["FAKE_RESULT_LISTING"], destination)
            raise SystemExit(0)
            ''',
        )
        self.fake_ssh_keygen = self.executable(
            "fake-ssh-keygen",
            r'''
            #!/usr/bin/env python3
            import sys
            if sys.argv[1:3] != ["-F", "f41-4242"] or "-f" not in sys.argv:
                raise SystemExit(2)
            print("f41-4242 ssh-ed25519 AAAATEST")
            ''',
        )

    def environment(
        self,
        *,
        launch_mode: str = "success",
        fail_ssh: str = "",
        transient_empty_inventories: int = 0,
        destroy_fail: bool = False,
        show_fail_on_call: int = 0,
        show_failure_transient_empty_inventories: int = 0,
        noisy_ssh: str = "",
        destroy_lies: bool = False,
        malformed_post_destroy_inventories: int = 0,
        destroy_fail_transient_empty_inventories: int = 0,
    ) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update(
            {
                "HOME": str(self.home),
                "OPENBAO_VASTAI_BIN": str(self.fake_wrapper),
                "F41_GIT_BIN": str(self.fake_git),
                "F41_SSH_BIN": str(self.fake_ssh),
                "F41_SCP_BIN": str(self.fake_scp),
                "F41_SSH_KEYGEN_BIN": str(self.fake_ssh_keygen),
                "VAST_SSH_IDENTITY_FILE": str(self.identity),
                "FAKE_STATE": str(self.root / "state.json"),
                "FAKE_EVENTS": str(self.events),
                "FAKE_EXPECTED_IMAGE": EXPECTED_IMAGE,
                "FAKE_SOURCE_REVISION": SOURCE_REVISION,
                "FAKE_OUTPUT_ROOT": str(self.output),
                "FAKE_JOB_ID": JOB_ID,
                "FAKE_BUNDLE_SHA": self.bundle_sha256,
                "FAKE_BUNDLE_SIZE": str(self.bundle.stat().st_size),
                "FAKE_RESULT_ARCHIVE": str(self.result_archive),
                "FAKE_RESULT_LISTING": str(self.result_listing),
                "FAKE_LAUNCH_MODE": launch_mode,
                "FAKE_FAIL_SSH_MATCH": fail_ssh,
                "FAKE_TRANSIENT_EMPTY_INVENTORIES": str(
                    transient_empty_inventories
                ),
                "FAKE_DESTROY_FAIL": "1" if destroy_fail else "0",
                "FAKE_SHOW_FAIL_ON_CALL": str(show_fail_on_call),
                "FAKE_SHOW_FAILURE_TRANSIENT_EMPTY_INVENTORIES": str(
                    show_failure_transient_empty_inventories
                ),
                "FAKE_NOISY_SSH_MATCH": noisy_ssh,
                "FAKE_DESTROY_LIES": "1" if destroy_lies else "0",
                "FAKE_MALFORMED_POST_DESTROY_INVENTORIES": str(
                    malformed_post_destroy_inventories
                ),
                "FAKE_DESTROY_FAIL_TRANSIENT_EMPTY_INVENTORIES": str(
                    destroy_fail_transient_empty_inventories
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environment

    def run_supervisor(
        self,
        *,
        launch_mode: str = "success",
        fail_ssh: str = "",
        transient_empty_inventories: int = 0,
        destroy_fail: bool = False,
        show_fail_on_call: int = 0,
        show_failure_transient_empty_inventories: int = 0,
        noisy_ssh: str = "",
        destroy_lies: bool = False,
        malformed_post_destroy_inventories: int = 0,
        destroy_fail_transient_empty_inventories: int = 0,
    ):
        return subprocess.run(
            [
                str(SUPERVISOR),
                "--offer-id",
                "12345",
                "--bundle",
                str(self.bundle),
                "--expected-sha256",
                self.bundle_sha256,
                "--source-revision",
                SOURCE_REVISION,
                "--expected-image",
                EXPECTED_IMAGE,
                "--job-id",
                JOB_ID,
                "--output-root",
                str(self.output),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
            env=self.environment(
                launch_mode=launch_mode,
                fail_ssh=fail_ssh,
                transient_empty_inventories=transient_empty_inventories,
                destroy_fail=destroy_fail,
                show_fail_on_call=show_fail_on_call,
                show_failure_transient_empty_inventories=(
                    show_failure_transient_empty_inventories
                ),
                noisy_ssh=noisy_ssh,
                destroy_lies=destroy_lies,
                malformed_post_destroy_inventories=(
                    malformed_post_destroy_inventories
                ),
                destroy_fail_transient_empty_inventories=(
                    destroy_fail_transient_empty_inventories
                ),
            ),
        )

    def events_text(self) -> str:
        return self.events.read_text(encoding="utf-8") if self.events.exists() else ""

    def test_shell_syntax_and_static_fail_closed_guards(self):
        syntax = subprocess.run(["sh", "-n", str(SUPERVISOR)], check=False)
        self.assertEqual(syntax.returncode, 0)
        source = SUPERVISOR.read_text(encoding="utf-8")
        for required in (
            "StrictHostKeyChecking=yes",
            "UpdateHostKeys=no",
            "HashKnownHosts=no",
            "HostKeyAlias=",
            "GlobalKnownHostsFile=/dev/null",
            "--signal=TERM --kill-after=60s 45m",
            "--exclude='{job}/.runtime'",
            "MAX_RESULT_ARCHIVE_BYTES = 512 * 1024**2",
            'self.prepare_attempt_identity()',
            '"--attempt-label"',
            "STABLE_ABSENCE_CONFIRMATIONS = 5",
            "CHILD_CLEANUP_PREFIX",
            "child_cleanup_attestation_invalid",
            "allow_attested_id_replacement=True",
            'self.destroy_owned("normal")',
            "self.validate_local_results(archive)",
        ):
            self.assertIn(required, source)
        self.assertNotIn("accept-new", source)
        self.assertNotIn("ssh-keyscan", source)
        self.assertLess(
            source.index('self.destroy_owned("normal")'),
            source.index("self.validate_local_results(archive)"),
        )
        self.assertTrue(SUPERVISOR.stat().st_mode & 0o111)

    def test_invalid_offer_never_calls_wrapper(self):
        completed = subprocess.run(
            [str(SUPERVISOR), "--offer-id", "0"],
            check=False,
            capture_output=True,
            text=True,
            env=self.environment(),
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(self.events.exists())

    def test_complete_run_destroys_before_local_validation(self):
        completed = self.run_supervisor()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(
            report["status"],
            "passed_remote_cad_archive_validated_instance_destroyed_not_released",
        )
        self.assertTrue(report["instance_destroyed_verified"])
        self.assertEqual(report["verified_artifact_count"], 18)
        self.assertFalse(report["simulation_validated"])
        events = self.events_text()
        self.assertEqual(events.count("wrapper:destroy\n"), 1)
        self.assertIn("ssh:917-cad-stage-job ", events)
        self.assertIn("ssh:/usr/bin/timeout --signal=TERM --kill-after=60s 45m", events)
        self.assertIn("ssh:set -eu\n", events)
        self.assertTrue((self.output / "validated" / JOB_ID).is_dir())
        known = self.home / ".cache/openbao-vastai/known-hosts/f41-4242"
        self.assertFalse(known.exists())

    def test_nonzero_launch_with_complete_json_is_destroyed(self):
        completed = self.run_supervisor(launch_mode="nonzero-json")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        self.assertFalse(
            (self.home / ".cache/openbao-vastai/known-hosts/f41-4242").exists()
        )

    def test_nonzero_launch_with_unique_stderr_label_is_reconciled_and_destroyed(self):
        completed = self.run_supervisor(launch_mode="nonzero-label-stderr")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        self.assertNotIn("destruction not verified", completed.stderr)

    def test_invalid_launch_gate_still_destroys_attributable_instance(self):
        completed = self.run_supervisor(launch_mode="invalid-gate")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("launch_gate_not_verified", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_wrong_image_blocks_workload_but_still_destroys_owned_instance(self):
        completed = self.run_supervisor(launch_mode="wrong-image")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("launch_image_mismatch", completed.stderr)
        self.assertNotIn("ssh:", self.events_text())
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["created"])

    def test_launch_without_child_output_uses_parent_identity_and_destroys(self):
        completed = self.run_supervisor(launch_mode="nonzero-noidentity")
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("destruction not verified", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        attempt_label = (self.output / "attempt-label.txt").read_text().strip()
        self.assertRegex(
            attempt_label,
            r"^3dprinting993-component-factory-f41-cad-[0-9a-f]{20}$",
        )

    def test_child_cleanup_receipt_plus_stable_absence_avoids_second_delete(self):
        completed = self.run_supervisor(launch_mode="child-cleanup-valid")
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotEqual(completed.returncode, 97)
        self.assertIn("paid_launch_command_failed:9", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 0)
        self.assertGreaterEqual(self.events_text().count("wrapper:instances\n"), 6)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["created"])
        self.assertFalse(
            (self.home / ".cache/openbao-vastai/known-hosts/f41-4242").exists()
        )

    def test_wrong_label_child_cleanup_receipt_cannot_prove_absence(self):
        completed = self.run_supervisor(
            launch_mode="child-cleanup-wrong-label-absent"
        )
        self.assertEqual(completed.returncode, 97)
        self.assertIn("CRITICAL: destruction not verified", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 0)

    def test_wrong_image_child_cleanup_receipt_requires_parent_delete(self):
        completed = self.run_supervisor(
            launch_mode="child-cleanup-wrong-image-live"
        )
        self.assertNotEqual(completed.returncode, 97)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_wrong_id_child_cleanup_receipt_requires_parent_delete(self):
        completed = self.run_supervisor(launch_mode="child-cleanup-wrong-id-live")
        self.assertNotEqual(completed.returncode, 97)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_false_child_cleanup_proof_requires_parent_delete(self):
        completed = self.run_supervisor(
            launch_mode="child-cleanup-false-proof-live"
        )
        self.assertNotEqual(completed.returncode, 97)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_duplicate_child_cleanup_receipt_requires_parent_delete(self):
        completed = self.run_supervisor(launch_mode="child-cleanup-duplicate-live")
        self.assertNotEqual(completed.returncode, 97)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_transport_failure_still_destroys(self):
        completed = self.run_supervisor(fail_ssh="917-cad-stage-job")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("remote_bundle_staging_failed", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)

    def test_transient_empty_inventory_does_not_fake_destruction(self):
        completed = self.run_supervisor(
            fail_ssh="917-cad-stage-job",
            transient_empty_inventories=5,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["created"])

    def test_destroy_outage_returns_dedicated_critical_code(self):
        completed = self.run_supervisor(
            fail_ssh="917-cad-stage-job",
            destroy_fail=True,
        )
        self.assertEqual(completed.returncode, 97)
        self.assertIn("CRITICAL: destruction not verified", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["created"])

    def test_failed_destroy_with_five_empty_snapshots_never_commits_absence(self):
        completed = self.run_supervisor(
            fail_ssh="917-cad-stage-job",
            destroy_fail=True,
            destroy_fail_transient_empty_inventories=5,
        )
        self.assertEqual(completed.returncode, 97)
        self.assertIn("CRITICAL: destruction not verified", completed.stderr)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["created"])
        self.assertTrue(
            (self.home / ".cache/openbao-vastai/known-hosts/f41-4242").exists()
        )

    def test_show_failure_and_transient_empty_inventory_still_destroy(self):
        completed = self.run_supervisor(
            show_fail_on_call=1,
            show_failure_transient_empty_inventories=1,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("show-after-launch_show_failed", completed.stderr)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["created"])

    def test_oversized_child_output_is_bounded_and_instance_destroyed(self):
        started = __import__("time").monotonic()
        completed = self.run_supervisor(noisy_ssh="917-cad-stage-job")
        elapsed = __import__("time").monotonic() - started
        self.assertNotEqual(completed.returncode, 0)
        self.assertLess(elapsed, 10)
        self.assertEqual(self.events_text().count("wrapper:destroy\n"), 1)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["created"])
        captures = list(self.output.glob("*.stdout")) + list(
            self.output.glob("*.stderr")
        )
        self.assertTrue(captures)
        self.assertLessEqual(
            max(path.stat().st_size for path in captures),
            2 * 1024 * 1024,
        )

    def test_malformed_absence_snapshots_cannot_prove_destruction(self):
        completed = self.run_supervisor(
            destroy_lies=True,
            malformed_post_destroy_inventories=5,
        )
        self.assertEqual(completed.returncode, 97)
        self.assertIn("CRITICAL: destruction not verified", completed.stderr)
        state = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["created"])


if __name__ == "__main__":
    unittest.main()
