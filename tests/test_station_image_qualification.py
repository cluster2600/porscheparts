import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "station_image_qualification",
    Path(__file__).resolve().parents[1] / "deploy/vast/station/qualify_image.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StationImageQualificationTests(unittest.TestCase):
    def registry(self, ports=None, sizes=None):
        config = json.dumps({"os": "linux", "architecture": "amd64", "config": {
            "ExposedPorts": dict.fromkeys(ports or ["22/tcp", "47998/udp"], {})}}).encode()
        manifest = json.dumps({"config": {"digest": "sha256:" + hashlib.sha256(config).hexdigest()},
                               "layers": [{"size": n} for n in (sizes if sizes is not None else [123, 456])]}).encode()
        reference = "ghcr.io/" + module.PACKAGE + "@sha256:" + hashlib.sha256(manifest).hexdigest()
        return reference, manifest, config

    def qualify(self, reference, manifest, config):
        replies = [io.BytesIO(b'{"token":"anonymous-test-token"}'), io.BytesIO(manifest), io.BytesIO(config)]
        with mock.patch.object(module.ssl, "create_default_context", return_value=mock.sentinel.tls), \
                mock.patch.object(module.urllib.request, "urlopen", side_effect=replies) as requests:
            result = module.qualify(reference)
        return result, requests.call_args_list

    def test_anonymous_pinned_manifest_config_and_compressed_layer_sum(self):
        self.assertEqual(module.PACKAGE, "cluster2600/3dprinting993-picogk-m64")
        reference, manifest, config = self.registry()
        result, calls = self.qualify(reference, manifest, config)
        self.assertTrue(result["anonymous_registry_verified"])
        self.assertEqual(result["image_ref"], reference)
        self.assertEqual(result["published_ports"], ["22/tcp", "47998/udp"])
        self.assertEqual(result["image_download_bytes"], 579 + len(manifest) + len(config))
        self.assertEqual(result["layer_count"], 2)
        self.assertFalse(calls[0].args[0].has_header("Authorization"))
        self.assertEqual(calls[1].args[0].get_header("Authorization"), "Bearer anonymous-test-token")
        self.assertTrue(calls[1].args[0].full_url.endswith(reference.split("@", 1)[1]))
        self.assertTrue(calls[2].args[0].full_url.endswith(result["config_digest"]))
        self.assertTrue(all(call.kwargs == {"context": mock.sentinel.tls, "timeout": 60} for call in calls))

    def test_tls_uses_mac_certificate_when_present_or_verified_system_context(self):
        reference, manifest, config = self.registry()
        for mac_ca_exists in (True, False):
            replies = [io.BytesIO(b'{"token":"anonymous-test-token"}'), io.BytesIO(manifest), io.BytesIO(config)]
            with self.subTest(mac_ca_exists=mac_ca_exists), \
                    mock.patch.object(module.Path, "is_file", return_value=mac_ca_exists), \
                    mock.patch.object(module.ssl, "create_default_context", return_value=mock.sentinel.tls) as context, \
                    mock.patch.object(module.urllib.request, "urlopen", side_effect=replies):
                module.qualify(reference)
            context.assert_called_once_with(**({"cafile": "/etc/ssl/cert.pem"} if mac_ca_exists else {}))

    def test_manifest_and_configuration_digest_mismatches_are_rejected(self):
        reference, manifest, config = self.registry()
        for payloads, error in [((manifest + b" ", config), "manifest digest mismatch"),
                                ((manifest, config + b" "), "configuration digest mismatch")]:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.qualify(reference, *payloads)

    def test_unexpected_published_port_is_rejected_even_with_valid_digests(self):
        with self.assertRaisesRegex(ValueError, "published ports violate"):
            self.qualify(*self.registry(ports=["22/tcp", "47998/udp", "8000/tcp"]))

    def test_other_package_is_rejected_before_any_registry_request(self):
        with mock.patch.object(module.urllib.request, "urlopen") as request, \
                self.assertRaisesRegex(ValueError, "exact station package"):
            module.qualify("ghcr.io/cluster2600/3dprinting993-picogk-station@sha256:" + "a" * 64)
        request.assert_not_called()

    def test_invalid_layer_sizes_cannot_understate_transfer_budget(self):
        for sizes in ([], [True], [-1], ["123"]):
            with self.subTest(sizes=sizes), self.assertRaisesRegex(ValueError, "invalid registry layer sizes"):
                self.qualify(*self.registry(sizes=sizes))


if __name__ == "__main__":
    unittest.main()
