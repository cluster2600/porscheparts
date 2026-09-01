import importlib.util
from importlib.machinery import SourceFileLoader
import os
import tempfile
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
    @classmethod
    def setUpClass(cls):
        cls.wrapper = load_wrapper()

    def test_scope_is_fixed_to_existing_github_secret_and_pinned_image(self):
        self.assertEqual(self.wrapper.ALLOWED_SECRET_PATH, "secrets/data/github")
        self.assertEqual(self.wrapper.GHCR_USERNAME, "cluster2600")
        self.assertRegex(self.wrapper.GHCR_DIGEST, r"^sha256:[0-9a-f]{64}$")
        self.assertIn(self.wrapper.GHCR_DIGEST, self.wrapper.GHCR_MANIFEST_URL)

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


if __name__ == "__main__":
    unittest.main()
