"""Tests locaux isolés : transport M64, aucun appel Vast/SSH/Bao réel."""
from contextlib import ExitStack, redirect_stdout
import base64
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def wrapper():
    loader = SourceFileLoader("m64_wrapper_test", str(ROOT / "deploy/openbao/openbao-vastai"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def encoded(data):
    return base64.b64encode(data).decode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class M64JobTests(unittest.TestCase):
    def setUp(self):
        self.w = wrapper()
        self.temp = tempfile.TemporaryDirectory(prefix="m64-wrapper-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.payload_root = self.root / "bundle"
        self.payload_root.mkdir(mode=0o700)
        self.manifest_path = self.payload_root / "manifest.json"
        self.instance_id = 123456
        self.label = self.w.SIMREADY_LABEL + "-" + "a" * 20
        phase = b"import argparse\np=argparse.ArgumentParser(); p.add_argument('--job-root'); p.parse_args()\n"
        self.code = {f"phases/{name}.py": phase for name in self.w.M64_PHASES}
        self.code["phases/common.py"] = b"# pinned common\n"
        self.code["skill/SKILL.md"] = b"# Synthetic offline fixture, no real NVIDIA runtime.\n"
        self.inputs = {name: b"synthetic fixture\n" for name in self.w.M64_INPUTS}
        self.rebuild()

    def rebuild(self):
        def entries(values):
            return [{"path": name, "size": len(data), "sha256": sha(data)} for name, data in sorted(values.items())]
        code_manifest = json.dumps({"schema_version": "1.0.0", "profile": self.w.M64_PROFILE, "files": entries(self.code)}, sort_keys=True).encode()
        self.w.M64_APPROVED_CODE_MANIFEST_SHA256 = sha(code_manifest)
        self.files = {**self.code, **self.inputs, "code-manifest.json": code_manifest}
        for name, data in self.files.items():
            path = self.payload_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        now = int(time.time())
        self.manifest = {
            "schema_version": "1.0.0", "profile": self.w.M64_PROFILE,
            "job_id": "m64-offline-test", "instance_id": self.instance_id, "label": self.label,
            "image": self.w.M64_SIMREADY_IMAGE, "created_epoch": now - 1,
            "deadline_epoch": now + 600, "max_dph": 2.5, "budget_usd": 5,
            "files": entries(self.files),
            "outputs": [{"path": "results/proof.json", "max_bytes": 4096}],
        }
        self.save()

    def save(self):
        self.manifest_path.write_text(json.dumps(self.manifest, sort_keys=True))

    def bundle(self):
        return self.w.m64_load_bundle(self.manifest_path, self.instance_id)

    def wire(self, operation="transfer", phase=None, seconds=30):
        manifest, data, files = self.bundle()
        return json.dumps({
            "operation": operation, "manifest_b64": encoded(data), "manifest_sha256": sha(data),
            "files_b64": {name: encoded(value) for name, value in files.items()} if operation == "transfer" else {},
            "phase": phase, "timeout_seconds": seconds,
        }).encode()

    def local_remote(self, wire):
        # Replace only deployment constants in the fixture. No actual SSH,
        # /workspace writes, installed wrapper, user identity or runtime are used.
        helper = self.w.M64_REMOTE_HELPER.replace("__M64_CODE_PIN__", self.w.M64_APPROVED_CODE_MANIFEST_SHA256)
        helper = helper.replace('Path("/workspace/jobs")', repr(self.root / "jobs").replace("PosixPath", "Path"))
        helper = helper.replace('"/opt/simready-validation/bin/python"', repr(sys.executable))
        result = subprocess.run([sys.executable, "-I", "-c", helper], input=wire, capture_output=True, timeout=20)
        self.assertEqual(result.stderr, b"")
        return result.returncode, json.loads(result.stdout)

    def test_valid_bundle_snapshots_exact_bytes_and_fixed_phase_registry(self):
        manifest, payload, files = self.bundle()
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(payload, self.manifest_path.read_bytes())
        self.assertEqual(files, self.files)
        self.assertIn("context", self.w.M64_PHASES)
        self.assertIn("profile-initial", self.w.M64_PHASES)

    def test_bad_phase_rejected_before_authentication(self):
        with mock.patch.object(self.w, "login") as login:
            for phase in ("render;id", "../../evil", "render --script /tmp/x", "unknown"):
                with self.subTest(phase=phase), self.assertRaises(self.w.SafeError):
                    self.w.run(["m64-phase", "123456", str(self.manifest_path), phase])
            login.assert_not_called()

    def test_manifest_bound_to_exact_instance_label_image_profile(self):
        for name, bad in (("instance_id", self.instance_id + 1), ("instance_id", True), ("label", "other"), ("image", "unapproved:latest"), ("image", self.w.SIMREADY_IMAGE), ("profile", "917")):
            old = self.manifest[name]
            with self.subTest(name=name, value=bad):
                self.manifest[name] = bad
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.bundle()
            self.manifest[name] = old

    def test_rejects_unpinned_code_even_with_self_consistent_job_hashes(self):
        self.w.M64_APPROVED_CODE_MANIFEST_SHA256 = None
        with self.assertRaisesRegex(self.w.SafeError, "not yet pinned"):
            self.bundle()
        self.w.M64_APPROVED_CODE_MANIFEST_SHA256 = "0" * 64
        with self.assertRaisesRegex(self.w.SafeError, "approved immutable"):
            self.bundle()

    def test_all_code_and_input_hashes_checked(self):
        for name in ("phases/common.py", "skill/SKILL.md", "inputs/assembly.step"):
            with self.subTest(name=name):
                path = self.payload_root / name
                original = path.read_bytes()
                path.write_bytes(b"x" * len(original))
                with self.assertRaisesRegex(self.w.SafeError, "declared size and SHA256"):
                    self.bundle()
                path.write_bytes(original)

    def test_rejects_relative_traversal_and_shell_path_injection(self):
        entry = self.manifest["files"][0]
        original = entry["path"]
        for value in ("/etc/passwd", "../evil", "inputs/../evil", "inputs/x;id", "inputs/$(id)", "inputs/x\nfoo", "inputs\\x", "inputs/.hidden"):
            with self.subTest(path=value):
                entry["path"] = value
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.bundle()
        entry["path"] = original

    def test_rejects_symlink_file_parent_and_hardlink(self):
        path = self.payload_root / "inputs/assembly.step"
        original = path.read_bytes()
        other = self.root / "other"
        other.write_bytes(original)
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(self.w.SafeError, "symlink"):
            self.bundle()
        path.unlink()
        os.link(other, path)
        with self.assertRaisesRegex(self.w.SafeError, "metadata"):
            self.bundle()
        path.unlink()
        path.write_bytes(original)
        (self.payload_root / "inputs").rename(self.payload_root / "real-inputs")
        (self.payload_root / "inputs").symlink_to(self.payload_root / "real-inputs", target_is_directory=True)
        with self.assertRaisesRegex(self.w.SafeError, "symlink"):
            self.bundle()

    def test_rejects_writable_file_duplicate_json_and_case_ambiguity(self):
        self.manifest_path.chmod(0o666)
        with self.assertRaisesRegex(self.w.SafeError, "metadata"):
            self.bundle()
        self.manifest_path.chmod(0o600)
        self.manifest_path.write_text('{"profile":"m64","profile":"917"}')
        with self.assertRaisesRegex(self.w.SafeError, "strict JSON"):
            self.bundle()
        self.save()
        self.manifest["files"].append(dict(self.manifest["files"][0], path=self.manifest["files"][0]["path"].upper()))
        self.save()
        with self.assertRaisesRegex(self.w.SafeError, "case-ambiguous"):
            self.bundle()

    def test_rejects_nonfinite_boolean_negative_and_over_budget_numbers(self):
        for name, value in (("budget_usd", float("nan")), ("budget_usd", float("inf")), ("budget_usd", True), ("budget_usd", 20.01), ("max_dph", -1), ("max_dph", 2.51), ("max_dph", False), ("budget_usd", 0.01), ("deadline_epoch", self.manifest["created_epoch"] + 7201)):
            old = self.manifest[name]
            with self.subTest(name=name, value=value):
                self.manifest[name] = value
                self.save()
                with self.assertRaises(self.w.SafeError):
                    self.bundle()
            self.manifest[name] = old

    def test_rejects_unlisted_code_missing_inputs_and_unsafe_outputs(self):
        self.manifest["files"].append({"path": "evil.py", "size": 0, "sha256": sha(b"")})
        (self.payload_root / "evil.py").write_bytes(b"")
        self.save()
        with self.assertRaisesRegex(self.w.SafeError, "undeclared code"):
            self.bundle()
        self.manifest["files"].pop()
        for path in ("inputs/secret", "results/../secret", "results/a;ls"):
            self.manifest["outputs"][0]["path"] = path
            self.save()
            with self.assertRaises(self.w.SafeError):
                self.bundle()

    def metadata(self):
        return {
            "id": self.instance_id, "label": self.label, "actual_status": "running",
            "image_uuid": self.w.M64_SIMREADY_IMAGE, "ssh_host": "ssh.example.test", "ssh_port": 12345,
            "dph_total": 2, "inet_up_cost": 0.01, "inet_down_cost": 0.01,
        }

    def mock_verified_dependencies(self, metadata=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name in ("verify_single_simready_instance", "verify_simready_contract", "m64_no_symlink_path", "validate_simready_known_hosts"):
            stack.enter_context(mock.patch.object(self.w, name))
        stack.enter_context(mock.patch.object(self.w, "read_local_ssh_public_key", return_value="synthetic approved public key"))
        stack.enter_context(mock.patch.object(self.w, "instance_lists_approved_ssh_key", return_value=True))
        stack.enter_context(mock.patch.object(self.w, "vast_request", return_value={"instances": metadata or self.metadata()}))
        return stack

    def test_strict_existing_knownhost_and_pair_checks_no_tofu(self):
        self.mock_verified_dependencies()
        command = self.w.m64_verified_ssh("synthetic", self.manifest, collecting=False)
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertNotIn("StrictHostKeyChecking=accept-new", command)
        for option in ("ForwardAgent=no", "ClearAllForwardings=yes", "IdentitiesOnly=yes", "BatchMode=yes"):
            self.assertIn(option, command)
        self.w.read_local_ssh_public_key.assert_called_once_with()
        self.w.verify_simready_contract.assert_called_once_with(
            "synthetic", self.instance_id, self.label, profile=self.w.M64_PROFILE)
        self.w.instance_lists_approved_ssh_key.assert_called_once_with("synthetic", self.instance_id, "synthetic approved public key")

    def test_wrong_remote_instance_rejected_even_for_rescue_collection(self):
        self.mock_verified_dependencies(dict(self.metadata(), id=self.instance_id + 1))
        with self.assertRaisesRegex(self.w.SafeError, "exact running instance"):
            self.w.m64_verified_ssh("synthetic", self.manifest, collecting=True)

    def test_transport_and_rescue_prefer_provider_direct_pair_with_strict_knownhost(self):
        metadata = dict(self.metadata(), public_ipaddr="1.1.1.1", ports={"22/tcp": [
            {"HostIp": "::", "HostPort": "32002"},
            {"HostIp": "0.0.0.0", "HostPort": "32001"},
        ]})
        self.mock_verified_dependencies(metadata)
        for collecting in (False, True):
            with self.subTest(collecting=collecting):
                command = self.w.m64_verified_ssh("synthetic", self.manifest, collecting=collecting)
                self.assertIn("root@1.1.1.1", command)
                self.assertNotIn("root@ssh.example.test", command)
                self.assertEqual(command[command.index("-p") + 1], "32001")
                self.assertIn("StrictHostKeyChecking=yes", command)
                self.assertIn(f"HostKeyAlias=simready-{self.instance_id}", command)

    def test_transport_refuses_malformed_direct_instead_of_proxy_even_for_collect(self):
        metadata = dict(self.metadata(), public_ipaddr="203.0.113.8", ports={"22/tcp": [{"HostPort": True}]})
        self.mock_verified_dependencies(metadata)
        for collecting in (False, True):
            with self.subTest(collecting=collecting), self.assertRaisesRegex(self.w.SafeError, "direct SSH endpoint is malformed"):
                self.w.m64_verified_ssh("synthetic", self.manifest, collecting=collecting)

    def test_legacy_image_is_rejected_even_for_rescue_collection(self):
        self.mock_verified_dependencies(dict(self.metadata(), image_uuid=self.w.SIMREADY_IMAGE))
        with self.assertRaisesRegex(self.w.SafeError, "exact running instance"):
            self.w.m64_verified_ssh("synthetic", self.manifest, collecting=True)

    def test_collect_survives_expired_deadline_and_incurred_rate_increase(self):
        self.mock_verified_dependencies(dict(self.metadata(), dph_total=100))
        self.manifest["created_epoch"] -= 1000
        self.manifest["deadline_epoch"] -= 1000
        self.w.m64_verified_ssh("synthetic", self.manifest, collecting=True)
        self.w.verify_simready_contract.assert_not_called()
        with self.assertRaisesRegex(self.w.SafeError, "deadline"):
            self.w.m64_verified_ssh("synthetic", self.manifest, collecting=False)

    def test_fresh_api_completion_does_not_reset_absolute_deadline(self):
        self.mock_verified_dependencies()
        with mock.patch.object(self.w.time, "time", side_effect=[self.manifest["created_epoch"] + 2, self.manifest["deadline_epoch"] + 1]):
            with self.assertRaisesRegex(self.w.SafeError, "deadline"):
                self.w.m64_verified_ssh("synthetic", self.manifest, collecting=False)

    def test_local_remote_roundtrip_verifies_snapshot_and_private_permissions(self):
        code, response = self.local_remote(self.wire())
        self.assertEqual(code, 0)
        self.assertEqual(response["operation"], "transfer")
        remote_root = self.root / "jobs" / self.manifest["job_id"]
        self.assertEqual(stat.S_IMODE(remote_root.stat().st_mode), 0o700)
        self.assertEqual((remote_root / "job-manifest.json").read_bytes(), self.manifest_path.read_bytes())
        for name, data in self.files.items():
            self.assertEqual((remote_root / name).read_bytes(), data)
            self.assertEqual(stat.S_IMODE((remote_root / name).stat().st_mode), 0o400)
        (remote_root / "results/proof.json").write_bytes(b'{"evidence":"synthetic"}')
        code, response = self.local_remote(self.wire("collect"))
        self.assertEqual(code, 0)
        destination = self.root / "private-results"
        receipt = self.w.m64_store_results(destination, self.manifest, response)
        self.assertTrue(receipt["retrieval_complete"])
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((destination / "results/proof.json").stat().st_mode), 0o600)
        self.assertNotIn("base64", (destination / "collection-receipt.json").read_text())

    def test_remote_refuses_retransfer_manifest_change_and_added_import_code(self):
        original_wire = self.wire()
        self.assertEqual(self.local_remote(original_wire)[0], 0)
        self.assertEqual(self.local_remote(original_wire)[0], 1)
        self.manifest["deadline_epoch"] += 1
        self.save()
        self.assertEqual(self.local_remote(self.wire("collect"))[0], 1)
        self.manifest["deadline_epoch"] -= 1
        self.save()
        remote = self.root / "jobs" / self.manifest["job_id"]
        (remote / "phases/evil.py").write_bytes(b"raise Exception('not allowed')")
        self.assertEqual(self.local_remote(self.wire("phase", "preflight"))[0], 1)

    def test_remote_refuses_symlink_output_or_code_before_reading(self):
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        remote = self.root / "jobs" / self.manifest["job_id"]
        target = self.root / "private-synthetic-do-not-read"
        target.write_text("synthetic sensitive data")
        (remote / "results/proof.json").symlink_to(target)
        code, response = self.local_remote(self.wire("collect"))
        self.assertEqual(code, 1)
        self.assertNotIn("synthetic sensitive", str(response))

    def test_phase_nonzero_keeps_job_and_allows_missing_output_collection(self):
        self.code["phases/preflight.py"] = b"raise SystemExit(7)\n"
        self.rebuild()
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        code, response = self.local_remote(self.wire("phase", "preflight"))
        self.assertEqual(code, 0)
        self.assertEqual(response["exit_code"], 7)
        self.assertFalse(response["timed_out"])
        self.assertTrue((self.root / "jobs" / self.manifest["job_id"]).exists())
        code, response = self.local_remote(self.wire("collect"))
        self.assertEqual(code, 0)
        self.assertEqual(response["missing_outputs"], ["results/proof.json"])

    def test_remote_phase_timeout_is_recorded_and_collectable(self):
        self.code["phases/preflight.py"] = b"import time\ntime.sleep(10)\n"
        self.rebuild()
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        code, response = self.local_remote(self.wire("phase", "preflight", seconds=1))
        self.assertEqual(code, 0)
        self.assertEqual(response["exit_code"], 124)
        self.assertTrue(response["timed_out"])
        self.assertEqual(self.local_remote(self.wire("collect"))[0], 0)

    def test_collect_hash_mismatch_extra_file_and_symlink_destination_rejected(self):
        value = b"synthetic"
        response = {"files": {"results/proof.json": {"size": len(value), "sha256": "0" * 64, "base64": encoded(value)}}, "missing_outputs": [], "present_outputs": ["results/proof.json"]}
        destination = self.root / "private-results"
        with self.assertRaisesRegex(self.w.SafeError, "hash"):
            self.w.m64_store_results(destination, self.manifest, response)
        self.assertFalse(destination.exists())
        response["files"]["results/proof.json"]["sha256"] = sha(value)
        response["files"]["results/undeclared.json"] = response["files"]["results/proof.json"]
        with self.assertRaisesRegex(self.w.SafeError, "inventory"):
            self.w.m64_store_results(destination, self.manifest, response)
        del response["files"]["results/undeclared.json"]
        destination.symlink_to(self.payload_root, target_is_directory=True)
        with self.assertRaisesRegex(self.w.SafeError, "new private"):
            self.w.m64_store_results(destination, self.manifest, response)

    def test_mocked_phase_operation_uses_fixed_command_and_does_not_print_remote_logs(self):
        bundle = self.bundle()
        def transport(command, payload, timeout):
            request = json.loads(payload)
            remote_argv = shlex.split(command[-1])
            self.assertEqual(remote_argv[:3], ["/opt/simready-validation/bin/python", "-I", "-c"])
            self.assertIn("fixed M64 transport contract rejected", remote_argv[3])
            self.assertEqual(request["files_b64"], {})
            self.assertEqual(request["phase"], "render")
            return json.dumps({"schema_version": "1.0.0", "job_id": self.manifest["job_id"], "instance_id": self.instance_id, "operation": "phase", "manifest_sha256": sha(bundle[1]), "phase": "render", "exit_code": 3, "timed_out": False}).encode()
        with mock.patch.object(self.w, "m64_verified_ssh", return_value=["ssh", "synthetic"]), mock.patch.object(self.w, "run_m64_transport", side_effect=transport), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.w.m64_operation("synthetic", ["m64-phase", str(self.instance_id), str(self.manifest_path), "render"], bundle), 1)
        self.assertEqual(json.loads(output.getvalue())["exit_code"], 3)

    def test_real_local_transport_timeout_and_stream_limit_do_not_echo_content(self):
        for code, timeout in (("import time; time.sleep(10)", 0.15), ("import sys; sys.stderr.write('synthetic-sensitive-' * 5000)", 3)):
            with self.subTest(code=code), self.assertRaises(self.w.SafeError) as raised:
                self.w.run_m64_transport([sys.executable, "-I", "-c", code], b"{}", timeout)
            self.assertNotIn("synthetic-sensitive", str(raised.exception))

    def test_recursive_outputs_collect_sidecars_and_enforce_aggregate_bound(self):
        self.manifest["outputs"] = [{"path": "results/render", "max_bytes": 10}]
        self.save()
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        remote = self.root / "jobs" / self.manifest["job_id"]
        output = remote / "results/render/images"
        output.mkdir(parents=True)
        (output / "frame-001.png").write_bytes(b"1234")
        (output / "frame-002.png").write_bytes(b"5678")
        code, response = self.local_remote(self.wire("collect"))
        self.assertEqual(code, 0)
        self.assertEqual(len(response["files"]), 2)
        self.assertEqual(response["present_outputs"], ["results/render"])
        destination = self.root / "recursive-private"
        self.assertTrue(self.w.m64_store_results(destination, self.manifest, response)["retrieval_complete"])
        self.assertEqual((destination / "results/render/images/frame-002.png").read_bytes(), b"5678")
        (output / "frame-003.png").write_bytes(b"abc")
        self.assertEqual(self.local_remote(self.wire("collect"))[0], 1)

    def test_recursive_local_response_limit_and_traversal_are_rechecked(self):
        self.manifest["outputs"] = [{"path": "results/render", "max_bytes": 4}]
        entry = {"size": 3, "sha256": sha(b"abc"), "base64": encoded(b"abc")}
        response = {"present_outputs": ["results/render"], "missing_outputs": [], "files": {"results/render/a": entry, "results/render/b": entry}}
        with self.assertRaisesRegex(self.w.SafeError, "recursive result bytes"):
            self.w.m64_store_results(self.root / "bad-results", self.manifest, response)
        response["files"] = {"results/render/../../escape": entry}
        with self.assertRaisesRegex(self.w.SafeError, "path"):
            self.w.m64_store_results(self.root / "bad-results", self.manifest, response)

    def test_recursive_symlink_directory_and_special_file_are_rejected(self):
        self.manifest["outputs"] = [{"path": "results/render", "max_bytes": 100}]
        self.save()
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        output = self.root / "jobs" / self.manifest["job_id"] / "results/render"
        output.mkdir()
        (output / "escape").symlink_to(self.payload_root, target_is_directory=True)
        self.assertEqual(self.local_remote(self.wire("collect"))[0], 1)
        (output / "escape").unlink()
        os.mkfifo(output / "fifo")
        self.assertEqual(self.local_remote(self.wire("collect"))[0], 1)

    def test_recursive_empty_root_and_missing_root_are_distinct(self):
        self.manifest["outputs"] = [{"path": "results/empty", "max_bytes": 100}, {"path": "results/missing", "max_bytes": 100}]
        self.save()
        self.assertEqual(self.local_remote(self.wire())[0], 0)
        (self.root / "jobs" / self.manifest["job_id"] / "results/empty").mkdir()
        code, response = self.local_remote(self.wire("collect"))
        self.assertEqual(code, 0)
        self.assertEqual(response["present_outputs"], ["results/empty"])
        self.assertEqual(response["missing_outputs"], ["results/missing"])
        receipt = self.w.m64_store_results(self.root / "partial", self.manifest, response)
        self.assertFalse(receipt["retrieval_complete"])

    def test_real_local_transport_handles_input_and_bounded_stdout(self):
        command = [sys.executable, "-I", "-c", "import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data)"]
        data = b"synthetic roundtrip" * 5000
        self.assertEqual(self.w.run_m64_transport(command, data, 3), data)

    def test_onstart_initializes_exact_embedded_helper_before_normal_start(self):
        self.assertEqual(self.w.simready_full_onstart_command(), "/usr/local/bin/simready-sshd-runtime-wrapper -T >/dev/null && simready-vast-onstart")
        self.assertNotIn("/usr/sbin/sshd", self.w.simready_full_onstart_command())
        # Source evidence of idempotent missing-only host-key generation;
        # this test is not a claim about provider-side live initialization.
        source = (ROOT / "containers/simready-sshd-runtime-wrapper.sh").read_text()
        self.assertIn("/usr/bin/ssh-keygen -A", source)
        self.assertIn('/usr/bin/flock -x 9', source)
        self.assertNotIn("rm -f /etc/ssh", source)


if __name__ == "__main__":
    unittest.main()
