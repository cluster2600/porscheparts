import base64
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = ROOT / "deploy" / "openbao" / "openbao-ghcr"


def load_wrapper():
    loader = SourceFileLoader("openbao_ghcr", str(WRAPPER_PATH))
    spec = importlib.util.spec_from_loader("openbao_ghcr", loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenBaoGhcrWrapperTest(unittest.TestCase):
    WORKFLOW_BYTES = b"name: Build compute images\n"

    @classmethod
    def setUpClass(cls):
        cls.wrapper = load_wrapper()

    def test_scope_is_fixed_to_existing_github_secret_and_pinned_image(self):
        self.assertEqual(self.wrapper.ALLOWED_SECRET_PATH, "secrets/data/github")
        self.assertEqual(self.wrapper.GHCR_USERNAME, "cluster2600")
        self.assertRegex(self.wrapper.GHCR_DIGEST, r"^sha256:[0-9a-f]{64}$")
        self.assertIn(self.wrapper.GHCR_DIGEST, self.wrapper.GHCR_MANIFEST_URL)
        self.assertNotIn(self.wrapper.GHCR_DIGEST, self.wrapper.GHCR_REVOKED_DIGESTS)
        self.assertGreaterEqual(len(self.wrapper.GHCR_REVOKED_DIGESTS), 2)

    def test_revoked_digest_is_rejected_before_registry_or_vast_use(self):
        revoked = next(iter(self.wrapper.GHCR_REVOKED_DIGESTS))
        with mock.patch.object(self.wrapper, "GHCR_DIGEST", revoked), self.assertRaisesRegex(
            self.wrapper.SafeError, "digest is revoked"
        ):
            self.wrapper.validate_pinned_digest()

        with (
            mock.patch.object(self.wrapper, "GHCR_DIGEST", revoked),
            mock.patch.object(
                self.wrapper.sys, "argv", ["openbao-ghcr", "--auth-check"]
            ),
            mock.patch.object(self.wrapper, "validate_bootstrap_metadata"),
            mock.patch.object(self.wrapper, "login") as login,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(self.wrapper.main(), 1)
            login.assert_not_called()

        self.wrapper.validate_pinned_digest()

    def test_direct_runtime_attestation_rejects_revoked_digest_before_evidence(self):
        revoked = next(iter(self.wrapper.GHCR_REVOKED_DIGESTS))
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(self.wrapper, "GHCR_DIGEST", revoked),
            mock.patch.object(self.wrapper, "validate_qualification_evidence") as qualify,
        ):
            with self.assertRaisesRegex(self.wrapper.SafeError, "digest is revoked"):
                self.wrapper.attest_runtime(
                    Path(directory) / "qualification.json",
                    Path(directory) / "attestation.json",
                    "job-f42b",
                    "a" * 32,
                )
        qualify.assert_not_called()

    def test_existing_token_alias_is_accepted_without_username_field(self):
        fake_token = "x" * 40
        payload = {"data": {"data": {"GITHUB_TOKEN": fake_token}}}
        with mock.patch.object(
            self.wrapper,
            "read_bootstrap_value",
            return_value=self.wrapper.ALLOWED_SECRET_PATH,
        ), mock.patch.object(self.wrapper, "request", return_value=(payload, {})):
            username, token = self.wrapper.read_credential("session-token")
        self.assertEqual(username, "cluster2600")
        self.assertEqual(token, fake_token)

    def test_unrelated_fields_are_rejected(self):
        payload = {"data": {"data": {"password": "x" * 40}}}
        with mock.patch.object(
            self.wrapper,
            "read_bootstrap_value",
            return_value=self.wrapper.ALLOWED_SECRET_PATH,
        ), mock.patch.object(self.wrapper, "request", return_value=(payload, {})):
            with self.assertRaises(self.wrapper.SafeError):
                self.wrapper.read_credential("session-token")

    def test_vast_command_never_receives_github_credential(self):
        captured = {}

        def fake_run(argv, *, check):
            captured["argv"] = argv
            captured["check"] = check
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "openbao-vastai"
            executable.touch(mode=0o700)
            os.chmod(executable, 0o700)
            with mock.patch.object(self.wrapper, "VAST_WRAPPER", executable), mock.patch.object(
                self.wrapper.subprocess,
                "run",
                side_effect=fake_run,
            ):
                result = self.wrapper.run_vast(["launch-vast-simready-heavy", "12345"])

        self.assertEqual(result, 0)
        self.assertEqual(captured["argv"], [str(executable), "launch-simready-heavy", "12345"])
        self.assertFalse(captured["check"])

    @staticmethod
    def qualification_payload(wrapper, digest, run_id=123456):
        return {
            "schema_version": "1.0.0",
            "status": wrapper.QUALIFIED_STATUS,
            "image_ref": f"ghcr.io/{wrapper.GHCR_REPOSITORY}@{digest}",
            "image_repository": f"ghcr.io/{wrapper.GHCR_REPOSITORY}",
            "manifest_digest": digest,
            "platform": "linux/amd64",
            "github_run_id": run_id,
            "github_run_url": (
                f"https://github.com/{wrapper.GITHUB_REPOSITORY}/actions/runs/{run_id}"
            ),
            "source_revision": "b" * 40,
            "source_branch": "codex/f42b-simready",
            "run_attempt": 2,
            "workflow_path": wrapper.WORKFLOW_PATH,
            "workflow_git_blob": wrapper.git_blob_sha1(
                OpenBaoGhcrWrapperTest.WORKFLOW_BYTES
            ),
            "checks": {key: True for key in wrapper.QUALIFICATION_CHECKS},
        }

    def test_runtime_attestation_is_exclusive_private_and_bound_to_wrapper(self):
        digest = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "qualification.json"
            output = root / "attestation.json"
            evidence.write_text(
                json.dumps(self.qualification_payload(self.wrapper, digest)) + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(self.wrapper, "GHCR_DIGEST", digest),
                mock.patch.object(self.wrapper, "anonymous_runtime_check") as public_check,
                mock.patch.object(
                    self.wrapper,
                    "github_runtime_check",
                    return_value=(789, "https://github.com/cluster2600/3dprinting993/actions/runs/123456/job/789"),
                ) as github_check,
                mock.patch.object(self.wrapper, "self_git_blob", return_value="c" * 40),
            ):
                self.wrapper.attest_runtime(
                    evidence, output, "job-f42b", "d" * 32
                )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(oct(output.stat().st_mode & 0o777), "0o600")
            self.assertEqual(payload["status"], "verified_public_runtime")
            self.assertEqual(payload["image_ref"], f"ghcr.io/{self.wrapper.GHCR_REPOSITORY}@{digest}")
            self.assertEqual(payload["github_job_id"], 789)
            self.assertEqual(payload["verified_steps"], self.wrapper.REQUIRED_STEPS)
            self.assertEqual(payload["attestor"]["git_blob"], "c" * 40)
            for field in (
                "source_revision",
                "source_branch",
                "run_attempt",
                "workflow_path",
                "workflow_git_blob",
            ):
                self.assertEqual(payload[field], self.qualification_payload(self.wrapper, digest)[field])
            self.assertEqual(payload["invocation"]["job_id"], "job-f42b")
            self.assertEqual(payload["invocation"]["nonce"], "d" * 32)
            self.assertEqual(
                payload["invocation"]["authenticity_scope"],
                "local_live_procedural_receipt_not_cryptographic_signature",
            )
            public_check.assert_called_once_with("b" * 40)
            github_check.assert_called_once()

            with self.assertRaisesRegex(
                self.wrapper.SafeError, "must be a new private file"
            ):
                self.wrapper.write_private_attestation(output, payload)

    def test_cli_attestation_forwards_qualification_output_job_id_and_nonce(self):
        qualification = Path("qualification.json")
        output = Path("attestation.json")
        operation = [
            "openbao-ghcr",
            self.wrapper.ATTESTOR_COMMAND,
            str(qualification),
            str(output),
            "job-f42b",
            "a" * 32,
        ]
        with (
            mock.patch.object(self.wrapper.sys, "argv", operation),
            mock.patch.object(self.wrapper, "validate_bootstrap_metadata"),
            mock.patch.object(self.wrapper, "validate_pinned_digest"),
            mock.patch.object(self.wrapper, "login", return_value="session"),
            mock.patch.object(
                self.wrapper,
                "read_credential",
                return_value=(self.wrapper.GHCR_USERNAME, "credential"),
            ),
            mock.patch.object(self.wrapper, "registry_auth_check"),
            mock.patch.object(self.wrapper, "revoke_token") as revoke,
            mock.patch.object(self.wrapper, "attest_runtime") as attest,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(self.wrapper.main(), 0)
        attest.assert_called_once_with(
            qualification, output, "job-f42b", "a" * 32
        )
        revoke.assert_called_once_with("session")

    def test_runtime_attestation_arguments_are_strict(self):
        digest = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            self.wrapper, "GHCR_DIGEST", digest
        ), mock.patch.object(
            self.wrapper, "validate_qualification_evidence"
        ) as qualify:
            root = Path(directory)
            for job_id in ("", "job/escape", "job with spaces", "j" * 65, None):
                with self.subTest(job_id=job_id), self.assertRaisesRegex(
                    self.wrapper.SafeError, "job id is invalid"
                ):
                    self.wrapper.attest_runtime(
                        root / "qualification.json",
                        root / "attestation.json",
                        job_id,
                        "a" * 32,
                    )
            for nonce in ("", "A" * 32, "a" * 31, "a" * 33, None):
                with self.subTest(nonce=nonce), self.assertRaisesRegex(
                    self.wrapper.SafeError, "nonce is invalid"
                ):
                    self.wrapper.attest_runtime(
                        root / "qualification.json",
                        root / "attestation.json",
                        "job-f42b",
                        nonce,
                    )
        qualify.assert_not_called()

    def test_qualification_requires_source_and_workflow_identity_fields(self):
        digest = "sha256:" + "a" * 64
        invalid_values = {
            "source_revision": (None, "b" * 39),
            "source_branch": (None, "bad branch"),
            "run_attempt": (True, 0),
            "workflow_path": (None, ".github/workflows/other.yml"),
            "workflow_git_blob": (None, "c" * 39),
        }
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            self.wrapper, "GHCR_DIGEST", digest
        ):
            evidence = Path(directory) / "qualification.json"
            for field, values in invalid_values.items():
                for value in values:
                    payload = self.qualification_payload(self.wrapper, digest)
                    payload[field] = value
                    evidence.write_text(json.dumps(payload) + "\n", encoding="utf-8")
                    with self.subTest(field=field, value=value), self.assertRaisesRegex(
                        self.wrapper.SafeError, "does not match the pinned image"
                    ):
                        self.wrapper.validate_qualification_evidence(evidence)

    def test_runtime_output_requires_private_non_symlink_parent_and_fstats_fd(self):
        payload = {"status": "unit-test"}
        real_fstat = os.fstat
        fstat_types = []

        def record_fstat(descriptor):
            info = real_fstat(descriptor)
            fstat_types.append((stat.S_ISDIR(info.st_mode), stat.S_ISREG(info.st_mode)))
            return info

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_parent = root / "private"
            private_parent.mkdir(mode=0o700)
            output = private_parent / "attestation.json"
            with mock.patch.object(self.wrapper.os, "fstat", side_effect=record_fstat):
                self.wrapper.write_private_attestation(output, payload)
            self.assertIn((False, True), fstat_types)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

            public_parent = root / "public"
            public_parent.mkdir(mode=0o755)
            with self.assertRaisesRegex(self.wrapper.SafeError, "private non-symlink"):
                self.wrapper.write_private_attestation(
                    public_parent / "attestation.json", payload
                )

            symlink_parent = root / "private-link"
            symlink_parent.symlink_to(private_parent, target_is_directory=True)
            with self.assertRaisesRegex(self.wrapper.SafeError, "private non-symlink"):
                self.wrapper.write_private_attestation(
                    symlink_parent / "other-attestation.json", payload
                )

    def github_payloads(self, evidence):
        run_url = evidence["github_run_url"]
        run = {
            "id": evidence["github_run_id"],
            "repository": {"full_name": self.wrapper.GITHUB_REPOSITORY},
            "name": "Build compute images",
            "path": self.wrapper.WORKFLOW_PATH,
            "status": "completed",
            "conclusion": "success",
            "head_sha": evidence["source_revision"],
            "head_branch": evidence["source_branch"],
            "run_attempt": evidence["run_attempt"],
            "html_url": run_url,
            "event": "workflow_dispatch",
        }
        workflow = {
            "type": "file",
            "path": self.wrapper.WORKFLOW_PATH,
            "sha": evidence["workflow_git_blob"],
            "encoding": "base64",
            "size": len(self.WORKFLOW_BYTES),
            "content": base64.b64encode(self.WORKFLOW_BYTES).decode("ascii"),
        }
        job_url = f"{run_url}/job/789"
        job = {
            "id": 789,
            "name": self.wrapper.REQUIRED_JOB_NAME,
            "status": "completed",
            "conclusion": "success",
            "html_url": job_url,
            "steps": [
                {"name": name, "conclusion": conclusion}
                for name, conclusion in self.wrapper.REQUIRED_STEPS.items()
            ],
        }
        return run, workflow, job, job_url

    def test_github_runtime_check_requires_the_exact_successful_job_steps(self):
        evidence = self.qualification_payload(
            self.wrapper, "sha256:" + "a" * 64
        )
        run, workflow, job, job_url = self.github_payloads(evidence)
        with mock.patch.object(
            self.wrapper,
            "request",
            side_effect=[(run, {}), (workflow, {}), ({"jobs": [job]}, {})],
        ):
            self.assertEqual(
                self.wrapper.github_runtime_check(evidence), (789, job_url)
            )

        job["steps"][-1]["conclusion"] = "skipped"
        with mock.patch.object(
            self.wrapper,
            "request",
            side_effect=[(run, {}), (workflow, {}), ({"jobs": [job]}, {})],
        ):
            with self.assertRaisesRegex(self.wrapper.SafeError, "steps are incomplete"):
                self.wrapper.github_runtime_check(evidence)

    def test_github_runtime_check_rejects_wrong_repo_path_branch_or_attempt(self):
        evidence = self.qualification_payload(self.wrapper, "sha256:" + "a" * 64)
        run, workflow, job, _ = self.github_payloads(evidence)
        mutations = (
            (("repository", "full_name"), "attacker/fork"),
            (("path",), ".github/workflows/other.yml"),
            (("head_branch",), "attacker-branch"),
            (("run_attempt",), evidence["run_attempt"] + 1),
        )
        for keys, value in mutations:
            changed = copy.deepcopy(run)
            if len(keys) == 2:
                changed[keys[0]][keys[1]] = value
            else:
                changed[keys[0]] = value
            with self.subTest(field=".".join(keys)), mock.patch.object(
                self.wrapper,
                "request",
                side_effect=[(changed, {}), (workflow, {}), ({"jobs": [job]}, {})],
            ), self.assertRaisesRegex(self.wrapper.SafeError, "expected success"):
                self.wrapper.github_runtime_check(evidence)

    def test_github_workflow_content_must_hash_to_qualified_git_blob(self):
        evidence = self.qualification_payload(self.wrapper, "sha256:" + "a" * 64)
        run, workflow, job, _ = self.github_payloads(evidence)
        workflow["content"] = base64.b64encode(
            self.WORKFLOW_BYTES + b"# injected\n"
        ).decode("ascii")
        workflow["size"] = len(self.WORKFLOW_BYTES) + len(b"# injected\n")
        with mock.patch.object(
            self.wrapper,
            "request",
            side_effect=[(run, {}), (workflow, {}), ({"jobs": [job]}, {})],
        ), self.assertRaisesRegex(self.wrapper.SafeError, "content does not match"):
            self.wrapper.github_runtime_check(evidence)

    def test_anonymous_runtime_check_requires_single_platform_manifest_and_exact_tags(self):
        digest = "sha256:" + "a" * 64
        manifest = {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "digest": "sha256:" + "d" * 64,
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "size": 4096,
            },
        }
        responses = [
            ({"token": "public-token"}, {}),
            (manifest, {"docker-content-digest": digest}),
            ({}, {"docker-content-digest": digest}),
            ({}, {"docker-content-digest": digest}),
        ]
        with (
            mock.patch.object(self.wrapper, "GHCR_DIGEST", digest),
            mock.patch.object(self.wrapper, "request", side_effect=responses) as request,
        ):
            self.wrapper.anonymous_runtime_check("b" * 40)
        requested_urls = [call.args[0] for call in request.call_args_list]
        self.assertEqual(
            requested_urls[1],
            f"https://ghcr.io/v2/{self.wrapper.GHCR_REPOSITORY}/manifests/{digest}",
        )
        self.assertEqual(
            requested_urls[2],
            f"https://ghcr.io/v2/{self.wrapper.GHCR_REPOSITORY}/manifests/{'b' * 40}",
        )
        self.assertEqual(
            requested_urls[3],
            f"https://ghcr.io/v2/{self.wrapper.GHCR_REPOSITORY}/manifests/latest",
        )

        manifest["mediaType"] = "application/vnd.oci.image.index.v1+json"
        with (
            mock.patch.object(self.wrapper, "GHCR_DIGEST", digest),
            mock.patch.object(self.wrapper, "request", side_effect=responses),
        ):
            with self.assertRaisesRegex(self.wrapper.SafeError, "not a single-platform"):
                self.wrapper.anonymous_runtime_check("b" * 40)

    def test_anonymous_runtime_check_rejects_each_movable_tag_mismatch(self):
        digest = "sha256:" + "a" * 64
        manifest = {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "digest": "sha256:" + "d" * 64,
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "size": 4096,
            },
        }
        for response_index, label in ((2, "source revision"), (3, "latest")):
            responses = [
                ({"token": "public-token"}, {}),
                (manifest, {"docker-content-digest": digest}),
                ({}, {"docker-content-digest": digest}),
                ({}, {"docker-content-digest": digest}),
            ]
            responses[response_index] = (
                {},
                {"docker-content-digest": "sha256:" + "e" * 64},
            )
            with self.subTest(tag=label), mock.patch.object(
                self.wrapper, "GHCR_DIGEST", digest
            ), mock.patch.object(
                self.wrapper, "request", side_effect=responses
            ), self.assertRaisesRegex(self.wrapper.SafeError, "does not resolve"):
                self.wrapper.anonymous_runtime_check("b" * 40)

    def test_request_refuses_cross_origin_redirect_without_forwarding_auth(self):
        origin_headers = []
        target_headers = []

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                target_headers.append(dict(self.headers))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format, *args):
                pass

        target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_url = f"http://127.0.0.1:{target.server_port}/capture"

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                origin_headers.append(dict(self.headers))
                self.send_response(302)
                self.send_header("Location", target_url)
                self.end_headers()

            def log_message(self, format, *args):
                pass

        origin = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        threads = [
            threading.Thread(target=server.serve_forever, daemon=True)
            for server in (target, origin)
        ]
        for thread in threads:
            thread.start()
        try:
            with mock.patch.object(
                self.wrapper, "TLS_CA_FILE", WRAPPER_PATH
            ), mock.patch.object(
                self.wrapper.ssl, "create_default_context", return_value=None
            ), self.assertRaisesRegex(
                self.wrapper.SafeError, "HTTP 302"
            ) as raised:
                self.wrapper.request(
                    f"http://127.0.0.1:{origin.server_port}/redirect",
                    headers={
                        "Authorization": "Bearer unit-test-auth",
                        "X-Vault-Token": "unit-test-vault",
                    },
                    source="redirect test",
                )
            self.assertEqual(len(origin_headers), 1)
            self.assertEqual(target_headers, [])
            self.assertNotIn("unit-test-auth", str(raised.exception))
            self.assertNotIn("unit-test-vault", str(raised.exception))
            for code in (301, 302, 303, 307, 308):
                self.assertIsNone(
                    self.wrapper.RejectRedirectHandler().redirect_request(
                        None, None, code, "redirect", {}, target_url
                    )
                )
        finally:
            for server in (origin, target):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
