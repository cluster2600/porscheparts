#!/usr/bin/env python3
"""Offline security-boundary tests for the dedicated Hugging Face wrapper."""

from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "deploy/openbao/openbao-huggingface"
FAKE_SESSION = "unit-test-bao-session"
FAKE_HF_TOKEN = "hf_" + "a" * 20
PRIVATE_DIAGNOSTIC = "unit-test-private-response-do-not-print"


def load_wrapper():
    loader = SourceFileLoader("openbao_huggingface", str(WRAPPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class OpenBaoHuggingFaceWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = load_wrapper()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bootstrap_dir = self.root / "bootstrap"
        self.bootstrap_dir.mkdir(mode=0o700)
        self.bootstrap_values = {"role_id": "unit-test-role", "secret_id": "unit-test-secret"}
        for name, value in self.bootstrap_values.items():
            path = self.bootstrap_dir / name
            path.write_text(value + "\n", encoding="ascii")
            path.chmod(0o600)
        config_patch = mock.patch.object(self.wrapper, "CONFIG_DIR", self.bootstrap_dir)
        config_patch.start()
        self.addCleanup(config_patch.stop)

    def response(self, url, *, body=b"{}", status=200):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.geturl.return_value = url
        response.read.return_value = body
        return response

    def run_main(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = self.wrapper.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_private_failure(self, result):
        code, stdout, stderr = result
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("OpenBao Hugging Face error: "))
        for private in (FAKE_SESSION, FAKE_HF_TOKEN, PRIVATE_DIAGNOSTIC):
            self.assertNotIn(private, stderr)
        self.assertNotIn("Traceback", stderr)

    def successful_request(self, url, *, token=None, payload=None):
        if url == self.wrapper.LOGIN_URL:
            self.assertIsNone(token)
            self.assertEqual(payload, self.bootstrap_values)
            return {"auth": {"client_token": FAKE_SESSION}}
        if url == self.wrapper.SECRET_URL:
            self.assertEqual(token, FAKE_SESSION)
            self.assertIsNone(payload)
            return {"data": {"data": {"HF_TOKEN": FAKE_HF_TOKEN}}}
        if url == self.wrapper.HF_ACCESS_URL:
            self.assertEqual(token, FAKE_HF_TOKEN)
            self.assertIsNone(payload)
            return {}
        if url == self.wrapper.REVOKE_URL:
            self.assertEqual(token, FAKE_SESSION)
            self.assertEqual(payload, {})
            return {}
        self.fail("unexpected request target")

    def test_endpoints_and_secret_scope_are_fixed(self):
        self.assertEqual(self.wrapper.ALLOWED_SECRET_PATH, "secrets/data/huggingface-flashnext")
        self.assertEqual(self.wrapper.BAO_BASE, "http://127.0.0.1:8200/v1/")
        self.assertEqual(self.wrapper.LOGIN_URL, "http://127.0.0.1:8200/v1/auth/codex-deploy/login")
        self.assertEqual(self.wrapper.SECRET_URL, "http://127.0.0.1:8200/v1/secrets/data/huggingface-flashnext")
        self.assertEqual(self.wrapper.REVOKE_URL, "http://127.0.0.1:8200/v1/auth/token/revoke-self")
        self.assertEqual(self.wrapper.MODEL_ID, "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4")
        self.assertEqual(self.wrapper.HF_ACCESS_URL, "https://huggingface.co/api/models/orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4/auth-check")

    def test_arbitrary_targets_are_rejected_before_building_a_request(self):
        targets = (
            "https://example.invalid/" + PRIVATE_DIAGNOSTIC,
            self.wrapper.SECRET_URL + "/",
            self.wrapper.SECRET_URL + "?path=other",
            self.wrapper.BAO_BASE + "secrets/data/github",
            self.wrapper.HF_ACCESS_URL.replace("https://", "http://"),
            self.wrapper.HF_ACCESS_URL.replace("huggingface.co", "huggingface.co.example.invalid"),
            "file:///" + PRIVATE_DIAGNOSTIC,
        )
        with mock.patch.object(self.wrapper.urllib.request, "build_opener") as build:
            for url in targets:
                with self.subTest(url=url), self.assertRaisesRegex(self.wrapper.SafeError, "fixed allowlist") as raised:
                    self.wrapper.request(url, token=FAKE_HF_TOKEN)
                self.assertNotIn(PRIVATE_DIAGNOSTIC, str(raised.exception))
        build.assert_not_called()

    def test_private_bootstrap_reads_only_the_two_expected_files(self):
        with mock.patch.object(self.wrapper.os, "read", wraps=os.read) as read:
            self.assertEqual(self.wrapper.bootstrap(read=True), self.bootstrap_values)
        self.assertEqual(read.call_count, 2)
        self.assertTrue(all(call.args[1] == 4097 for call in read.call_args_list))

    def test_check_validates_metadata_without_reading_credentials_or_http(self):
        # Invalid contents intentionally remain invisible to the metadata-only check.
        (self.bootstrap_dir / "secret_id").write_bytes(b"\xff\n")
        with (
            mock.patch.object(self.wrapper.os, "read", side_effect=AssertionError("must not read")) as read,
            mock.patch.object(self.wrapper.socket, "create_connection") as connect,
            mock.patch.object(self.wrapper, "request") as request,
        ):
            code, stdout, stderr = self.run_main(["--check"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), {"bootstrap_metadata_ok": True, "credentials_read": False})
        read.assert_not_called()
        request.assert_not_called()
        connect.assert_called_once_with(("127.0.0.1", 8200), timeout=2)

    def test_check_fails_safely_when_local_openbao_is_unavailable(self):
        with mock.patch.object(self.wrapper.socket, "create_connection", side_effect=OSError(PRIVATE_DIAGNOSTIC)):
            result = self.run_main(["--check"])
        self.assert_private_failure(result)
        self.assertIn("not listening on local loopback", result[2])

    def test_bootstrap_directory_requires_exact_private_mode(self):
        for mode in (0o500, 0o710, 0o750, 0o770, 0o777, 0o1700):
            with self.subTest(mode=oct(mode)):
                self.bootstrap_dir.chmod(mode)
                with self.assertRaises(self.wrapper.SafeError):
                    self.wrapper.bootstrap(read=False)
        self.bootstrap_dir.chmod(0o700)

    def test_bootstrap_rejects_missing_directory_symlink_and_wrong_type(self):
        link = self.root / "linked-bootstrap"
        link.symlink_to(self.bootstrap_dir, target_is_directory=True)
        regular_file = self.root / "not-a-directory"
        regular_file.write_bytes(b"fake")
        for target in (self.root / "missing", link, regular_file):
            with self.subTest(target=target.name), mock.patch.object(self.wrapper, "CONFIG_DIR", target):
                with self.assertRaisesRegex(self.wrapper.SafeError, "missing or unsafe"):
                    self.wrapper.bootstrap(read=False)

    def test_bootstrap_directory_and_files_require_current_ownership(self):
        real_fstat = os.fstat
        for wrong_type in (stat.S_ISDIR, stat.S_ISREG):
            def wrong_owner(fd):
                info = real_fstat(fd)
                values = {field: getattr(info, field) for field in ("st_uid", "st_mode", "st_nlink", "st_size")}
                if wrong_type(info.st_mode):
                    values["st_uid"] = os.getuid() + 1
                return SimpleNamespace(**values)

            with self.subTest(kind=wrong_type.__name__), mock.patch.object(self.wrapper.os, "fstat", side_effect=wrong_owner):
                with self.assertRaises(self.wrapper.SafeError):
                    self.wrapper.bootstrap(read=False)

    def test_bootstrap_files_require_exact_private_mode(self):
        for name in self.bootstrap_values:
            path = self.bootstrap_dir / name
            for mode in (0o400, 0o640, 0o660, 0o666, 0o700, 0o1600):
                with self.subTest(name=name, mode=oct(mode)):
                    path.chmod(mode)
                    with self.assertRaises(self.wrapper.SafeError):
                        self.wrapper.bootstrap(read=False)
            path.chmod(0o600)

    def test_bootstrap_rejects_missing_files_symlinks_and_hardlinks(self):
        for name in self.bootstrap_values:
            path = self.bootstrap_dir / name
            saved = self.root / (name + "-saved")
            path.rename(saved)
            with self.subTest(name=name, kind="missing"), self.assertRaises(self.wrapper.SafeError):
                self.wrapper.bootstrap(read=False)
            path.symlink_to(saved)
            with self.subTest(name=name, kind="symlink"), self.assertRaises(self.wrapper.SafeError):
                self.wrapper.bootstrap(read=False)
            path.unlink()
            os.link(saved, path)
            with self.subTest(name=name, kind="hardlink"), self.assertRaises(self.wrapper.SafeError):
                self.wrapper.bootstrap(read=False)
            path.unlink()
            saved.rename(path)

    def test_bootstrap_rejects_directories_and_fifos_as_files(self):
        path = self.bootstrap_dir / "secret_id"
        path.unlink()
        path.mkdir(mode=0o600)
        with self.assertRaises(self.wrapper.SafeError):
            self.wrapper.bootstrap(read=False)
        path.rmdir()
        os.mkfifo(path, mode=0o600)
        with self.assertRaises(self.wrapper.SafeError):
            self.wrapper.bootstrap(read=False)

    def test_bootstrap_file_size_bounds_apply_even_without_reading(self):
        path = self.bootstrap_dir / "secret_id"
        for size, accepted in ((0, False), (1, True), (4096, True), (4097, False)):
            path.write_bytes(b"a" * size)
            with self.subTest(size=size):
                if accepted:
                    self.assertEqual(self.wrapper.bootstrap(read=False), {})
                    self.assertEqual(len(self.wrapper.bootstrap(read=True)["secret_id"]), size)
                else:
                    with self.assertRaises(self.wrapper.SafeError):
                        self.wrapper.bootstrap(read=False)

    def test_bootstrap_rejects_invalid_ascii_and_format(self):
        for value in (b"\xff", b"\n", b"contains spaces", b"bad\x00value", b"bad\nvalue", b"bad/value"):
            (self.bootstrap_dir / "secret_id").write_bytes(value)
            with self.subTest(value=value), self.assertRaises(self.wrapper.SafeError):
                self.wrapper.bootstrap(read=True)

    def test_bootstrap_closes_all_open_descriptors_on_read_failure(self):
        real_open, real_close = os.open, os.close
        with (
            mock.patch.object(self.wrapper.os, "open", wraps=real_open) as opened,
            mock.patch.object(self.wrapper.os, "close", wraps=real_close) as closed,
            mock.patch.object(self.wrapper.os, "read", side_effect=OSError(PRIVATE_DIAGNOSTIC)),
        ):
            result = self.run_main(["--auth-check"])
        self.assert_private_failure(result)
        self.assertEqual(opened.call_count, 2)
        self.assertEqual(closed.call_count, 2)
        self.assertEqual(len({call.args[0] for call in closed.call_args_list}), 2)

    def test_hf_token_accepts_only_exact_field_and_bounded_format(self):
        for value in ("hf_" + "a" * 17, "hf_" + "Z9" * 100, "hf_" + "a" * 4093):
            with self.subTest(length=len(value)), mock.patch.object(self.wrapper, "request", return_value={"data": {"data": {"HF_TOKEN": value}}}) as request:
                self.assertEqual(self.wrapper.read_credential(FAKE_SESSION), value)
                request.assert_called_once_with(self.wrapper.SECRET_URL, token=FAKE_SESSION)
        invalid = (None, True, 42, [], {}, "", "hf_" + "a" * 16, "hf_" + "a" * 4094, "HF_" + "a" * 20, FAKE_HF_TOKEN + "\n", FAKE_HF_TOKEN + " ", "hf_" + "_" * 20)
        for value in invalid:
            with self.subTest(value_type=type(value).__name__, length=len(value) if isinstance(value, str) else None), mock.patch.object(self.wrapper, "request", return_value={"data": {"data": {"HF_TOKEN": value}}}):
                with self.assertRaisesRegex(self.wrapper.SafeError, "valid HF_TOKEN field"):
                    self.wrapper.read_credential(FAKE_SESSION)
        for payload in ({}, {"data": None}, {"data": []}, {"data": {"data": []}}, {"data": {"data": {"token": FAKE_HF_TOKEN}}}, {"HF_TOKEN": FAKE_HF_TOKEN}):
            with self.subTest(payload_type=str(type(payload))), mock.patch.object(self.wrapper, "request", return_value=payload):
                with self.assertRaises(self.wrapper.SafeError):
                    self.wrapper.read_credential(FAKE_SESSION)

    def test_auth_success_revokes_session_and_prints_only_evidence(self):
        with mock.patch.object(self.wrapper, "request", side_effect=self.successful_request) as request:
            code, stdout, stderr = self.run_main(["--auth-check"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), {
            "model_id": self.wrapper.MODEL_ID,
            "repository_read_access_verified": True,
            "bao_session_revoked": True,
            "weights_downloaded": False,
            "runtime_ready": False,
        })
        self.assertEqual([call.args[0] for call in request.call_args_list], [self.wrapper.LOGIN_URL, self.wrapper.SECRET_URL, self.wrapper.HF_ACCESS_URL, self.wrapper.REVOKE_URL])
        for private in (FAKE_SESSION, FAKE_HF_TOKEN, *self.bootstrap_values.values()):
            self.assertNotIn(private, stdout)

    def test_secret_and_hf_failures_still_revoke_the_session(self):
        for failing_url in (self.wrapper.SECRET_URL, self.wrapper.HF_ACCESS_URL):
            def fail_request(url, **kwargs):
                if url == failing_url:
                    raise self.wrapper.SafeError("request rejected")
                return self.successful_request(url, **kwargs)

            with self.subTest(target=failing_url), mock.patch.object(self.wrapper, "request", side_effect=fail_request) as request:
                self.assert_private_failure(self.run_main(["--auth-check"]))
                self.assertEqual(request.call_args, mock.call(self.wrapper.REVOKE_URL, token=FAKE_SESSION, payload={}))
                self.assertEqual(sum(call.args[0] == self.wrapper.REVOKE_URL for call in request.call_args_list), 1)

    def test_invalid_hf_credential_revokes_without_calling_hugging_face(self):
        def invalid_secret(url, **kwargs):
            if url == self.wrapper.SECRET_URL:
                return {"data": {"data": {"HF_TOKEN": PRIVATE_DIAGNOSTIC}}}
            return self.successful_request(url, **kwargs)

        with mock.patch.object(self.wrapper, "request", side_effect=invalid_secret) as request:
            self.assert_private_failure(self.run_main(["--auth-check"]))
        self.assertEqual([call.args[0] for call in request.call_args_list], [self.wrapper.LOGIN_URL, self.wrapper.SECRET_URL, self.wrapper.REVOKE_URL])

    def test_revocation_failure_cannot_report_success(self):
        def failed_revoke(url, **kwargs):
            if url == self.wrapper.REVOKE_URL:
                raise self.wrapper.SafeError("OpenBao connection failed")
            return self.successful_request(url, **kwargs)

        with mock.patch.object(self.wrapper, "request", side_effect=failed_revoke) as request:
            self.assert_private_failure(self.run_main(["--auth-check"]))
        self.assertEqual(request.call_args, mock.call(self.wrapper.REVOKE_URL, token=FAKE_SESSION, payload={}))

    def test_unexpected_post_login_failure_is_suppressed_and_revoked(self):
        def failed_request(url, **kwargs):
            if url == self.wrapper.HF_ACCESS_URL:
                raise RuntimeError(PRIVATE_DIAGNOSTIC + FAKE_HF_TOKEN)
            return self.successful_request(url, **kwargs)

        with mock.patch.object(self.wrapper, "request", side_effect=failed_request) as request:
            result = self.run_main(["--auth-check"])
        self.assert_private_failure(result)
        self.assertIn("details suppressed", result[2])
        self.assertEqual(request.call_args, mock.call(self.wrapper.REVOKE_URL, token=FAKE_SESSION, payload={}))

    def test_invalid_login_session_never_reaches_secret_or_hugging_face(self):
        for auth in (None, [], {}, {"client_token": None}, {"client_token": 42}, {"client_token": ""}, {"client_token": "bad\nvalue"}, {"client_token": "a" * 4097}):
            with self.subTest(auth_type=type(auth).__name__), mock.patch.object(self.wrapper, "request", return_value={"auth": auth}) as request:
                self.assert_private_failure(self.run_main(["--auth-check"]))
                request.assert_called_once_with(self.wrapper.LOGIN_URL, payload=self.bootstrap_values)

    def test_requests_disable_environment_proxies_and_use_separate_token_headers(self):
        for url, expected_header, unexpected_header in ((self.wrapper.SECRET_URL, "X-vault-token", "Authorization"), (self.wrapper.HF_ACCESS_URL, "Authorization", "X-vault-token")):
            response = self.response(url)
            opener = mock.Mock()
            opener.open.return_value = response
            environment = {"HTTP_PROXY": "http://example.invalid:9", "HTTPS_PROXY": "http://example.invalid:9", "ALL_PROXY": "http://example.invalid:9"}
            with self.subTest(url=url), mock.patch.dict(os.environ, environment), mock.patch.object(self.wrapper.urllib.request, "build_opener", return_value=opener) as build:
                self.assertEqual(self.wrapper.request(url, token=FAKE_HF_TOKEN), {})
            handlers = build.call_args.args
            proxies = [handler for handler in handlers if isinstance(handler, self.wrapper.urllib.request.ProxyHandler)]
            self.assertEqual(len(proxies), 1)
            self.assertEqual(proxies[0].proxies, {})
            self.assertTrue(any(isinstance(handler, self.wrapper.RejectRedirectHandler) for handler in handlers))
            https = next(handler for handler in handlers if isinstance(handler, self.wrapper.urllib.request.HTTPSHandler))
            self.assertTrue(https._context.check_hostname)
            self.assertEqual(https._context.verify_mode, self.wrapper.ssl.CERT_REQUIRED)
            req = opener.open.call_args.args[0]
            self.assertEqual(req.full_url, url)
            self.assertEqual(req.get_header(expected_header), ("Bearer " if url == self.wrapper.HF_ACCESS_URL else "") + FAKE_HF_TOKEN)
            self.assertIsNone(req.get_header(unexpected_header))
            self.assertEqual(req.get_method(), "GET")
            self.assertIsNone(req.data)
            self.assertEqual(opener.open.call_args.kwargs, {"timeout": self.wrapper.TIMEOUT_SECONDS})

    def test_hf_success_never_reads_a_response_body(self):
        response = self.response(self.wrapper.HF_ACCESS_URL, body=FAKE_HF_TOKEN.encode())
        with mock.patch.object(self.wrapper.urllib.request, "build_opener") as build:
            build.return_value.open.return_value = response
            self.assertEqual(self.wrapper.request(self.wrapper.HF_ACCESS_URL, token=FAKE_HF_TOKEN), {})
        response.read.assert_not_called()

    def test_hf_requires_200_and_all_requests_require_unchanged_url(self):
        for url, status, returned_url in ((self.wrapper.HF_ACCESS_URL, 204, self.wrapper.HF_ACCESS_URL), (self.wrapper.SECRET_URL, 201, self.wrapper.SECRET_URL), (self.wrapper.SECRET_URL, 200, "https://example.invalid/" + PRIVATE_DIAGNOSTIC)):
            response = self.response(returned_url, status=status)
            with self.subTest(status=status, url=url), mock.patch.object(self.wrapper.urllib.request, "build_opener") as build:
                build.return_value.open.return_value = response
                with self.assertRaises(self.wrapper.SafeError) as raised:
                    self.wrapper.request(url, token=FAKE_HF_TOKEN)
            self.assertNotIn(PRIVATE_DIAGNOSTIC, str(raised.exception))
            response.read.assert_not_called()

    def test_openbao_json_is_bounded_and_must_be_an_object(self):
        cases = (
            (b"{}", {}),
            (b"", {}),
            (b" " * (self.wrapper.MAX_RESPONSE_BYTES - 2) + b"{}", {}),
            (b"x" * (self.wrapper.MAX_RESPONSE_BYTES + 1), None),
            (PRIVATE_DIAGNOSTIC.encode(), None),
            (b"\xff", None),
            (b"[]", None),
            (b"null", None),
            (b"42", None),
        )
        for body, expected in cases:
            response = self.response(self.wrapper.SECRET_URL, body=body)
            with self.subTest(size=len(body), prefix=body[:10]), mock.patch.object(self.wrapper.urllib.request, "build_opener") as build:
                build.return_value.open.return_value = response
                if expected is None:
                    with self.assertRaises(self.wrapper.SafeError) as raised:
                        self.wrapper.request(self.wrapper.SECRET_URL, token=FAKE_SESSION)
                    self.assertNotIn(PRIVATE_DIAGNOSTIC, str(raised.exception))
                else:
                    self.assertEqual(self.wrapper.request(self.wrapper.SECRET_URL, token=FAKE_SESSION), expected)
            response.read.assert_called_once_with(self.wrapper.MAX_RESPONSE_BYTES + 1)

    def test_request_failures_hide_remote_details_tokens_and_body(self):
        for error_type in ("http", "url", "os", "timeout"):
            private = PRIVATE_DIAGNOSTIC + FAKE_SESSION + FAKE_HF_TOKEN
            if error_type == "http":
                body = io.BytesIO(private.encode())
                error = self.wrapper.urllib.error.HTTPError(self.wrapper.LOGIN_URL, 403, private, {}, body)
            elif error_type == "url":
                error = self.wrapper.urllib.error.URLError(private)
            elif error_type == "os":
                error = OSError(private)
            else:
                error = TimeoutError(private)
            with self.subTest(error_type=error_type), mock.patch.object(self.wrapper.urllib.request, "build_opener") as build:
                build.return_value.open.side_effect = error
                self.assert_private_failure(self.run_main(["--auth-check"]))
            if error_type == "http":
                self.assertTrue(body.closed)

    def test_redirects_are_not_followed_by_the_real_http_stack(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append((self.path, self.headers.get("X-Vault-Token")))
                if self.path == "/source":
                    self.send_response(302)
                    self.send_header("Location", "/would-leak-token")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"{}")

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:" + str(server.server_port) + "/source"
            with mock.patch.object(self.wrapper, "SECRET_URL", url):
                with self.assertRaisesRegex(self.wrapper.SafeError, "HTTP 302"):
                    self.wrapper.request(url, token=FAKE_SESSION)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(observed, [("/source", FAKE_SESSION)])

    def test_invalid_cli_never_echoes_arguments_or_reads_bootstrap(self):
        invalid = ([], ["--help"], ["--auth-check", FAKE_HF_TOKEN], ["--secret-path", PRIVATE_DIAGNOSTIC], ["--check", "--auth-check"], ["--export"])
        with mock.patch.object(self.wrapper, "bootstrap") as bootstrap, mock.patch.object(self.wrapper, "request") as request:
            for args in invalid:
                with self.subTest(args_count=len(args)):
                    result = self.run_main(args)
                    self.assert_private_failure(result)
                    self.assertEqual(result[2], "OpenBao Hugging Face error: usage: openbao-huggingface --check|--auth-check\n")
        bootstrap.assert_not_called()
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
