"""Gardes statiques de l'image transport Vast F40."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "containers/917-engine-wave-f40-vast"
DOCKERFILE = IMAGE_ROOT / "Dockerfile"
DOCKERIGNORE = IMAGE_ROOT / "Dockerfile.dockerignore"
LOCK = IMAGE_ROOT / "lock.json"
SYSTEM_PACKAGES = IMAGE_ROOT / "system-packages.sha256"
STAGE = IMAGE_ROOT / "stage_job.py"
RUN_JOB = IMAGE_ROOT / "run_job.sh"
PREPARE = IMAGE_ROOT / "prepare_layout.sh"
SMOKE = IMAGE_ROOT / "image_smoke.py"
ONSTART = IMAGE_ROOT / "vast_onstart.sh"
ENTRYPOINT = IMAGE_ROOT / "entrypoint.sh"
WORKFLOW = ROOT / ".github/workflows/917-engine-wave-f40-vast-image.yml"
DOC = ROOT / "docs/917_VAST_WAVE_IMAGE_F40.md"

F39_BASE = (
    "ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:"
    "742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3"
)
EXPECTED_PACKAGES = {
    "libbsd0": "0.11.7-2",
    "libcbor0.8": "0.8.0-2+b1",
    "libedit2": "3.1-20221030-2",
    "libfido2-1": "1.12.0-2+b1",
    "libproc2-0": "2:4.0.2-3",
    "libwrap0": "7.6.q-32",
    "openssh-client": "1:9.2p1-2+deb12u10",
    "openssh-server": "1:9.2p1-2+deb12u10",
    "openssh-sftp-server": "1:9.2p1-2+deb12u10",
    "procps": "2:4.0.2-3",
    "runit-helper": "2.15.2",
    "sensible-utils": "0.0.17+nmu1",
    "ucf": "3.0043+nmu1+deb12u1",
}


def load_stage_module():
    spec = importlib.util.spec_from_file_location("f40_vast_stage_job", STAGE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load stage_job.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EngineWaveF40VastImageTests(unittest.TestCase):
    def test_dockerfile_extends_exact_f39_digest_and_keeps_transport_root_bounded(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        lower = source.lower()
        for fragment in (
            f"ARG F39_BASE_IMAGE={F39_BASE}",
            "FROM ${F39_BASE_IMAGE} AS engine-wave-f40-vast",
            'test "${TARGETARCH}" = "amd64"',
            "openssh-server=1:9.2p1-2+deb12u10",
            "apt-get download",
            "sha256sum --check /tmp/system-packages.sha256",
            "DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/debs/*.deb",
            "rm -f /etc/ssh/ssh_host_*_key",
            "test ! -e /root/.ssh/authorized_keys",
            "USER 0:0",
            'ENTRYPOINT ["/opt/917-engine-wave-f40-vast/entrypoint.sh"]',
            "917-wave-run-job impose UID/GID 9139:9139",
        ):
            self.assertIn(fragment, source)
        self.assertEqual(source.count("FROM "), 1)
        self.assertNotIn("expose 22", lower)
        for forbidden in (
            "copy .",
            "raw-scans",
            "copy work",
            "copy twins",
            "copy catalog",
            "openbao",
            "id_vastai",
            "curl ",
            "wget ",
            "cuda",
            "physicsnemo",
            "omniverse",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotRegex(
            source,
            r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)",
        )

    def test_package_lock_matches_every_exact_apt_pin(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["system_packages"], EXPECTED_PACKAGES)
        source = DOCKERFILE.read_text(encoding="utf-8")
        pins = {}
        for package in EXPECTED_PACKAGES:
            match = re.search(
                rf"^\s+{re.escape(package)}=([^ \\\n]+) \\?$", source, re.MULTILINE
            )
            self.assertIsNotNone(match, package)
            pins[package] = match.group(1)
        self.assertEqual(pins, EXPECTED_PACKAGES)
        entries = re.findall(
            r"^([0-9a-f]{64})  ([A-Za-z0-9%+_.:-]+\.deb)$",
            SYSTEM_PACKAGES.read_text(encoding="ascii"),
            re.MULTILINE,
        )
        self.assertEqual(len(entries), len(EXPECTED_PACKAGES))
        self.assertEqual(len({digest for digest, _ in entries}), len(entries))
        self.assertEqual(len({filename for _, filename in entries}), len(entries))
        self.assertIn(
            (
                "933cd92a2329f9bf26d22660a834ae18ebdbe8df9c6127e4d9fcb098dac9cf72",
                "openssh-server_1%3a9.2p1-2+deb12u10_amd64.deb",
            ),
            entries,
        )
        artifact_lock = lock["system_package_artifact_lock"]
        self.assertEqual(artifact_lock["artifact_count"], len(entries))
        self.assertTrue(artifact_lock["verification_before_install"])
        self.assertEqual(
            hashlib.sha256(SYSTEM_PACKAGES.read_bytes()).hexdigest(),
            artifact_lock["sha256"],
        )

    def test_build_context_is_exact_public_allowlist(self):
        patterns = [
            line
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(
            patterns,
            [
                "**",
                "!containers/",
                "!containers/917-engine-wave-f40-vast/",
                "!containers/917-engine-wave-f40-vast/lock.json",
                "!containers/917-engine-wave-f40-vast/system-packages.sha256",
                "!containers/917-engine-wave-f40-vast/stage_job.py",
                "!containers/917-engine-wave-f40-vast/run_job.sh",
                "!containers/917-engine-wave-f40-vast/prepare_layout.sh",
                "!containers/917-engine-wave-f40-vast/image_smoke.py",
                "!containers/917-engine-wave-f40-vast/vast_onstart.sh",
                "!containers/917-engine-wave-f40-vast/entrypoint.sh",
            ],
        )

    def test_lock_is_prepublication_and_all_engine_claims_remain_closed(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["phase"], "F40-vast-image")
        self.assertEqual(lock["image"]["base_immutable_reference"], F39_BASE)
        self.assertIsNone(lock["image"]["digest"])
        self.assertIsNone(lock["image"]["immutable_reference"])
        gates = lock["gates"]
        for gate in (
            "linux_amd64_build_verified",
            "ghcr_digest_published",
            "ghcr_anonymous_pull_verified",
            "vast_authorized_key_injection_verified",
            "vast_ssh_direct_handshake_verified",
            "f40_campaign_executed_in_this_image",
            "engine_model_physically_correlated",
            "target_1600_mechanical_hp_proven",
            "engine_start_authorized",
            "manufacturing_authorized",
        ):
            self.assertIs(gates[gate], False, gate)
        self.assertFalse(lock["security_contract"]["embedded_secrets"])
        self.assertFalse(lock["security_contract"]["embedded_private_assets"])
        self.assertFalse(lock["security_contract"]["baked_authorized_keys"])
        self.assertFalse(lock["security_contract"]["baked_ssh_host_keys"])

    def test_stager_rejects_traversal_links_devices_duplicates_and_oversize(self):
        module = load_stage_module()

        valid = tarfile.TarInfo("public/repo.txt")
        valid.size = 8
        self.assertEqual(module.validate_members([valid]), 8)

        invalid_members: list[tuple[tarfile.TarInfo, str]] = []
        traversal = tarfile.TarInfo("../escape")
        invalid_members.append((traversal, "parent"))
        absolute = tarfile.TarInfo("/escape")
        invalid_members.append((absolute, "absolute"))
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "target"
        invalid_members.append((link, "special"))
        device = tarfile.TarInfo("device")
        device.type = tarfile.CHRTYPE
        invalid_members.append((device, "special"))
        oversized = tarfile.TarInfo("huge")
        oversized.size = module.MAX_SINGLE_FILE_BYTES + 1
        invalid_members.append((oversized, "limit"))
        for member, expected in invalid_members:
            with self.assertRaisesRegex(module.StagingError, expected):
                module.validate_members([member])
        duplicate_a = tarfile.TarInfo("same")
        duplicate_b = tarfile.TarInfo("same")
        with self.assertRaisesRegex(module.StagingError, "duplicate"):
            module.validate_members([duplicate_a, duplicate_b])

    def test_scripts_parse_and_privilege_launcher_is_fail_closed(self):
        ast.parse(STAGE.read_text(encoding="utf-8"))
        ast.parse(SMOKE.read_text(encoding="utf-8"))
        for script in (RUN_JOB, PREPARE, ONSTART, ENTRYPOINT):
            completed = subprocess.run(
                ["sh", "-n", str(script)], capture_output=True, text=True, check=False
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

        launcher = RUN_JOB.read_text(encoding="utf-8")
        for fragment in (
            'SOLVER_UID=9139',
            'SOLVER_GID=9139',
            'run_job_requires_root_orchestrator',
            '--reuid="${SOLVER_UID}"',
            '--regid="${SOLVER_GID}"',
            "--clear-groups",
            "--inh-caps=-all",
            "--ambient-caps=-all",
            "--bounding-set=-all",
            "--no-new-privs",
            "env -i",
            'test ! -L "${directory}"',
        ):
            self.assertIn(fragment, launcher)
        self.assertNotIn("sudo", launcher)

        onstart = ONSTART.read_text(encoding="utf-8")
        self.assertIn('test -s "${authorized_keys}"', onstart)
        self.assertIn('chmod 0600 "${authorized_keys}"', onstart)
        self.assertIn('--expect-runtime-authorized-keys', onstart)
        self.assertIn('"f40_campaign_executed": False', onstart)

    def test_smoke_separates_packaging_from_real_vast_and_engine_evidence(self):
        source = SMOKE.read_text(encoding="utf-8")
        for fragment in (
            '"sshd_started_by_image_smoke": False',
            '"baked_authorized_keys": False',
            '"runtime_authorized_keys_present": authorized_keys.exists()',
            '"solver_no_new_privileges": identity["no_new_privs"] == "1"',
            '"vast_entrypoint_injection_executed": False',
            '"vast_authorized_key_injection_verified": False',
            '"vast_ssh_direct_handshake_verified": False',
            '"f40_campaign_executed": False',
            '"target_1600_mechanical_hp_proven": False',
            '"engine_start_authorized": False',
            '"manufacturing_authorized": False',
        ):
            self.assertIn(fragment, source)

    def test_workflow_publishes_amd64_digest_and_requires_anonymous_pull(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "${{ github.sha }}-vast-f40",
            "steps.build.outputs.digest",
            "Gate anonymous pull of the exact digest",
            "DOCKER_CONFIG=\"${anonymous_config}\" docker pull --platform linux/amd64",
            "--user 9139:9139",
            "--cap-add DAC_OVERRIDE",
            "--cap-add FOWNER",
            "--cap-add SETPCAP",
            "target_1600_mechanical_hp_proven == false",
        ):
            self.assertIn(fragment, source)
        for forbidden in (
            "pull_request_target",
            "create instance",
            "launch-wave",
            "rent",
            "openbao-vastai",
            "VAST_API_KEY",
            "NVIDIA_API_KEY",
        ):
            self.assertNotIn(forbidden, source)

    def test_no_private_material_or_key_blob_is_embedded(self):
        for path in IMAGE_ROOT.iterdir():
            if not path.is_file():
                continue
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", source)
            self.assertNotIn("BEGIN RSA PRIVATE KEY", source)
            self.assertNotRegex(source, r"ssh-(?:rsa|ed25519) [A-Za-z0-9+/]{40,}")
            self.assertNotIn("935+Xtreme", source)
            self.assertNotIn("raw-scans/", source)

    def test_documentation_explains_vast_entrypoint_and_limits(self):
        source = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "runtype: ssh_direct",
            "onstart: /usr/local/bin/917-wave-vast-onstart",
            "Vast remplace ENTRYPOINT",
            "917-wave-stage-job",
            "917-wave-run-job",
            "Le GPU 3060 Ti n'accélère pas Aeolus1D",
            "1 600 ch",
            "https://docs.vast.ai/api-reference/creating-instances-with-api",
            "https://docs.vast.ai/guides/instances/docker-environment",
        ):
            self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
