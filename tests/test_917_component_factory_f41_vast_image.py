"""Gardes statiques de l'image Vast CPU/CAO F41."""

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
IMAGE_ROOT = ROOT / "containers/917-component-factory-f41-vast"
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
SSHD_RUNTIME_WRAPPER = IMAGE_ROOT / "sshd_runtime_wrapper.sh"
WORKFLOW = ROOT / ".github/workflows/917-component-factory-f41-vast-image.yml"
DOC = ROOT / "docs/917_COMPONENT_FACTORY_F41_VAST_IMAGE.md"

F28_BASE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
)
USD_BASE = (
    "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
    "41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe"
)
F41_BUNDLE_ROOT = "917-component-factory-f41"
F41_BUNDLE_BUILDER = (
    ROOT / "twins/reference-917-engine/source/build_component_factory_bundle_f41.py"
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
    spec = importlib.util.spec_from_file_location("f41_vast_stage_job", STAGE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load stage_job.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_bundle(
    files: dict[str, bytes],
    *,
    digest_override: dict[str, str] | None = None,
    manifest_override: dict[str, object] | None = None,
) -> io.BytesIO:
    digest_override = digest_override or {}
    entries = [
        {
            "mode": "0755" if name.endswith((".py", ".sh")) else "0644",
            "path": name,
            "sha256": digest_override.get(name, hashlib.sha256(payload).hexdigest()),
            "size_bytes": len(payload),
        }
        for name, payload in sorted(files.items())
    ]
    manifest = {
        "all_payload_files_utf8_text": True,
        "archive_member_count": len(entries) + 1,
        "binary_payload_included": False,
        "bundle_root": F41_BUNDLE_ROOT,
        "file_count": len(entries),
        "files": entries,
        "newly_generated_geometry_included": False,
        "phase": "F41",
        "private_absolute_path_included": False,
        "public_remote_refs": ["refs/remotes/origin/main"],
        "raw_scan_included": False,
        "required_runtime_images": [F28_BASE, USD_BASE],
        "schema_version": "1.1.0",
        "secret_included": False,
        "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
        "source_revision": "a" * 40,
        "status": "public_transfer_bundle_file_manifest",
    }
    manifest.update(manifest_override or {})
    all_files = {
        f"{F41_BUNDLE_ROOT}/BUNDLE-MANIFEST.json": (
            json.dumps(manifest, sort_keys=True) + "\n"
        ).encode("utf-8"),
        **{f"{F41_BUNDLE_ROOT}/{name}": payload for name, payload in files.items()},
    }
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, payload in all_files.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            relative = name.removeprefix(f"{F41_BUNDLE_ROOT}/")
            member.mode = 0o755 if relative.endswith((".py", ".sh")) else 0o644
            member.mtime = 0
            archive.addfile(member, io.BytesIO(payload))
    stream.seek(0)
    return stream


class ComponentFactoryF41VastImageTests(unittest.TestCase):
    def test_dockerfile_extends_exact_f28_digest_and_adds_only_bounded_transport(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        lower = source.lower()
        for fragment in (
            f"ARG F28_BASE_IMAGE={F28_BASE}",
            "FROM ${F28_BASE_IMAGE} AS component-factory-f41-vast",
            'test "${TARGETARCH}" = "amd64"',
            "openssh-server=1:9.2p1-2+deb12u10",
            "apt-get download",
            "sha256sum --check /tmp/system-packages.sha256",
            "DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/debs/*.deb",
            "mv /usr/sbin/sshd /usr/lib/openssh/sshd.real",
            "rm -f /etc/ssh/ssh_host_*_key",
            "test ! -e /root/.ssh/authorized_keys",
            "install -o root -g root -m 0600 /dev/null /root/.no_auto_tmux",
            "USER 0:0",
            'ENTRYPOINT ["/opt/917-component-factory-f41-vast/entrypoint.sh"]',
            "sshd_runtime_wrapper.sh /usr/sbin/sshd",
            "917-cad-run-job",
            "9178:9178",
        ):
            self.assertIn(fragment, source)
        self.assertEqual(source.count("FROM "), 1)
        self.assertNotIn("expose 22", lower)
        for forbidden in (
            "copy .",
            "copy work",
            "copy twins",
            "copy catalog",
            "openbao",
            "id_vastai",
            "curl ",
            "wget ",
            "cuda",
            "physicsnemo",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotRegex(
            source,
            r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)",
        )

    def test_package_lock_matches_every_exact_apt_pin_and_hash(self):
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
        self.assertTrue(artifact_lock["verification_before_install"])
        self.assertEqual(artifact_lock["artifact_count"], len(entries))
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
                "!containers/917-component-factory-f41-vast/",
                "!containers/917-component-factory-f41-vast/lock.json",
                "!containers/917-component-factory-f41-vast/system-packages.sha256",
                "!containers/917-component-factory-f41-vast/stage_job.py",
                "!containers/917-component-factory-f41-vast/run_job.sh",
                "!containers/917-component-factory-f41-vast/prepare_layout.sh",
                "!containers/917-component-factory-f41-vast/image_smoke.py",
                "!containers/917-component-factory-f41-vast/vast_onstart.sh",
                "!containers/917-component-factory-f41-vast/entrypoint.sh",
                "!containers/917-component-factory-f41-vast/sshd_runtime_wrapper.sh",
            ],
        )

    def test_lock_is_prepublication_and_all_claims_remain_closed(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["phase"], "F41-vast-cad-image")
        self.assertEqual(lock["image"]["base_immutable_reference"], F28_BASE)
        self.assertEqual(lock["image"]["cad_user"], "9178:9178")
        self.assertEqual(lock["image"]["additional_local_image_size_bytes_max"], 16_000_000)
        self.assertIsNone(lock["image"]["digest"])
        self.assertIsNone(lock["image"]["immutable_reference"])
        wrapper = lock["wrapper_contract"]
        self.assertEqual(wrapper["runtype"], "ssh_direct")
        self.assertEqual(wrapper["onstart"], "/usr/local/bin/917-cad-vast-onstart")
        self.assertEqual(wrapper["ready_path"], "/workspace/READY")
        self.assertEqual(wrapper["runtime_image_ref_injected_by_launcher"], F28_BASE)
        bundle = lock["public_bundle_contract"]
        self.assertEqual(bundle["bundle_root"], F41_BUNDLE_ROOT)
        self.assertEqual(bundle["manifest_schema_version"], "1.1.0")
        self.assertEqual(
            bundle["source_repository_state_required"],
            "clean_commit_visible_at_exact_remote_ref",
        )
        self.assertTrue(bundle["payloads_read_from_git_head_not_worktree"])
        self.assertFalse(bundle["development_worktree_as_bundle_source_allowed"])
        self.assertFalse(bundle["geometry_payloads_allowed"])
        gates = lock["gates"]
        for gate in (
            "linux_amd64_build_verified",
            "ghcr_digest_published",
            "ghcr_anonymous_pull_verified",
            "vast_authorized_key_injection_verified",
            "vast_ssh_direct_handshake_verified",
            "f41_component_factory_executed_in_this_image",
            "f41_geometry_dimensionally_validated",
            "engine_model_physically_correlated",
            "omniverse_simready_validated",
            "target_1600_mechanical_hp_proven",
            "engine_start_authorized",
            "manufacturing_authorized",
        ):
            self.assertIs(gates[gate], False, gate)
        security = lock["security_contract"]
        self.assertTrue(security["vast_invokes_sshd_before_onstart"])
        self.assertEqual(security["sshd_runtime_wrapper"], "/usr/sbin/sshd")
        self.assertEqual(security["sshd_real_binary"], "/usr/lib/openssh/sshd.real")
        self.assertEqual(security["runtime_host_key_command"], "/usr/bin/ssh-keygen -A")
        self.assertTrue(security["runtime_host_keys_generated_before_real_sshd"])
        self.assertFalse(security["runtime_host_keys_persist_beyond_instance"])
        self.assertEqual(security["no_auto_tmux_marker"], "/root/.no_auto_tmux")
        self.assertEqual(security["no_auto_tmux_marker_owner_mode"], "0:0:0600")
        self.assertTrue(security["noninteractive_ssh_auto_tmux_disabled"])
        self.assertFalse(security["embedded_secrets"])
        self.assertFalse(security["embedded_private_assets"])
        self.assertFalse(security["baked_authorized_keys"])
        self.assertFalse(security["baked_ssh_host_keys"])

    def test_public_bundle_requires_exact_manifest_hashes_and_utf8_text(self):
        module = load_stage_module()
        source_name = "twins/reference-917-engine/source/execute_component_factory_f41.py"
        stream = public_bundle({source_name: b"print('public')\n"})
        with tarfile.open(fileobj=stream, mode="r:") as archive:
            result = module.validate_public_bundle(archive, archive.getmembers())
        self.assertEqual(result["payload_file_count"], 1)
        self.assertEqual(result["bundle_root"], F41_BUNDLE_ROOT)
        self.assertEqual(result["source_revision"], "a" * 40)
        self.assertEqual(result["public_remote_refs"], ["refs/remotes/origin/main"])

        mismatch = public_bundle(
            {source_name: b"print('public')\n"},
            digest_override={source_name: "0" * 64},
        )
        with tarfile.open(fileobj=mismatch, mode="r:") as archive:
            with self.assertRaisesRegex(module.StagingError, "digest_mismatch"):
                module.validate_public_bundle(archive, archive.getmembers())

        binary = public_bundle({source_name: b"public\0binary"})
        with tarfile.open(fileobj=binary, mode="r:") as archive:
            with self.assertRaisesRegex(module.StagingError, "binary_payload"):
                module.validate_public_bundle(archive, archive.getmembers())

        key_marker = public_bundle(
            {source_name: b"-----BEGIN OPENSSH PRIVATE KEY-----\n"}
        )
        with tarfile.open(fileobj=key_marker, mode="r:") as archive:
            with self.assertRaisesRegex(module.StagingError, "private_key_material"):
                module.validate_public_bundle(archive, archive.getmembers())

        dirty = public_bundle(
            {source_name: b"print('public')\n"},
            manifest_override={"source_repository_state": "local_worktree"},
        )
        with tarfile.open(fileobj=dirty, mode="r:") as archive:
            with self.assertRaisesRegex(module.StagingError, "source_repository_state"):
                module.validate_public_bundle(archive, archive.getmembers())

        local_ref = public_bundle(
            {source_name: b"print('public')\n"},
            manifest_override={"public_remote_refs": ["refs/heads/local-only"]},
        )
        with tarfile.open(fileobj=local_ref, mode="r:") as archive:
            with self.assertRaisesRegex(module.StagingError, "public_remote_ref"):
                module.validate_public_bundle(archive, archive.getmembers())

    def test_stager_rejects_other_geometry_private_paths_links_devices_and_traversal(self):
        module = load_stage_module()
        invalid: list[tuple[tarfile.TarInfo, str]] = []
        for name, expected in (
            ("../escape.py", "parent"),
            ("/escape.py", "absolute"),
            (f"{F41_BUNDLE_ROOT}/raw-scans/head.py", "private_or_repository"),
            (f"{F41_BUNDLE_ROOT}/source/model.step", "bundle_path_not_allowlisted"),
            (f"{F41_BUNDLE_ROOT}/id_vastai", "secret_filename"),
        ):
            invalid.append((tarfile.TarInfo(name), expected))
        link = tarfile.TarInfo(f"{F41_BUNDLE_ROOT}/source/link.py")
        link.type = tarfile.SYMTYPE
        link.linkname = "target.py"
        invalid.append((link, "special"))
        device = tarfile.TarInfo(f"{F41_BUNDLE_ROOT}/source/device.py")
        device.type = tarfile.CHRTYPE
        invalid.append((device, "special"))
        for member, expected in invalid:
            with self.assertRaisesRegex(module.StagingError, expected):
                module.validate_members([member])
        duplicate_a = tarfile.TarInfo(
            f"{F41_BUNDLE_ROOT}/twins/reference-917-engine/source/execute_component_factory_f41.py"
        )
        duplicate_b = tarfile.TarInfo(duplicate_a.name)
        with self.assertRaisesRegex(module.StagingError, "duplicate"):
            module.validate_members([duplicate_a, duplicate_b])

    def test_stager_allowlist_matches_the_text_only_f41_builder(self):
        module = load_stage_module()
        tree = ast.parse(F41_BUNDLE_BUILDER.read_text(encoding="utf-8"))
        allowlist = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "ALLOWLIST"
                for target in node.targets
            ):
                allowlist = ast.literal_eval(node.value)
                break
        self.assertIsNotNone(allowlist)
        allowed = set(module.ALLOWED_BUNDLE_RELATIVE_FILES)
        self.assertEqual(allowed, {*allowlist, "REMOTE_JOB.md"})
        self.assertTrue(allowed)
        for path in allowed:
            self.assertTrue(
                Path(path).name in module.ALLOWED_BASENAMES
                or Path(path).suffix.lower() in module.ALLOWED_SUFFIXES
            )

    def test_scripts_parse_and_cad_launcher_is_fail_closed(self):
        ast.parse(STAGE.read_text(encoding="utf-8"))
        ast.parse(SMOKE.read_text(encoding="utf-8"))
        for script in (RUN_JOB, PREPARE, ONSTART, ENTRYPOINT, SSHD_RUNTIME_WRAPPER):
            completed = subprocess.run(
                ["sh", "-n", str(script)], capture_output=True, text=True, check=False
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        launcher = RUN_JOB.read_text(encoding="utf-8")
        for fragment in (
            "CAD_UID=9178",
            "CAD_GID=9178",
            f"F41_RUNTIME_IMAGE_REF='{F28_BASE}'",
            "run_job_requires_root_orchestrator",
            '--reuid="${CAD_UID}"',
            '--regid="${CAD_GID}"',
            "--clear-groups",
            "--inh-caps=-all",
            "--ambient-caps=-all",
            "--bounding-set=-all",
            "--no-new-privs",
            "env -i",
            'CAD_RESULTS_DIR="${results_dir}"',
        ):
            self.assertIn(fragment, launcher)
        self.assertNotIn("sudo", launcher)
        onstart = ONSTART.read_text(encoding="utf-8")
        self.assertIn('test -s "${authorized_keys}"', onstart)
        self.assertIn('chmod 0600 "${authorized_keys}"', onstart)
        self.assertIn("no_auto_tmux=/root/.no_auto_tmux", onstart)
        self.assertIn('[ -e "${no_auto_tmux}" ] || [ -L "${no_auto_tmux}" ]', onstart)
        self.assertIn('rm -f -- "${no_auto_tmux}"', onstart)
        self.assertIn('install -o root -g root -m 0600 /dev/null "${no_auto_tmux}"', onstart)
        self.assertIn("f41-runtime-host-keys.ready", onstart)
        self.assertIn("--expect-runtime-authorized-keys", onstart)
        self.assertIn('"f41_component_factory_executed": False', onstart)
        sshd_wrapper = SSHD_RUNTIME_WRAPPER.read_text(encoding="utf-8")
        for fragment in (
            "real_sshd=/usr/lib/openssh/sshd.real",
            "runtime_dir=/run/sshd",
            'install -d -o root -g root -m 0755 "${runtime_dir}"',
            "host_key_marker=${runtime_dir}/f41-runtime-host-keys.ready",
            "/usr/bin/ssh-keygen -A",
            "stat -c '%u:%g:%a'",
            '"0:0:600"',
            'exec "${real_sshd}" "$@"',
        ):
            self.assertIn(fragment, sshd_wrapper)
        self.assertNotIn("PRIVATE KEY", sshd_wrapper)

    def test_smoke_executes_build123d_step_after_privilege_drop_and_closes_claims(self):
        source = SMOKE.read_text(encoding="utf-8")
        for fragment in (
            "from build123d import Align, Box, Cylinder, Pos, export_step, import_step",
            "export_step(source, step_path)",
            "reopened = import_step(step_path)",
            '"cad_effective_uid": probe["uid"]',
            '"cad_no_new_privileges": probe["no_new_privileges"]',
            '"transferred_payloads_utf8_text_only": True',
            '"synthetic_source_provenance_live_verified": False',
            '"lib3mf": version("lib3mf")',
            '"synthetic_step_roundtrip_executed": True',
            '"sshd_started": False',
            '"sshd_runtime_wrapper_installed": True',
            '"noninteractive_ssh_auto_tmux_disabled": True',
            '"runtime_host_keys_generated_by_wrapper": (',
            '"vast_authorized_key_injection_verified": False',
            '"vast_ssh_direct_handshake_verified": False',
            '"f41_component_factory_executed": False',
            '"f41_geometry_dimensionally_validated": False',
            '"omniverse_simready_validated": False',
            '"target_1600_mechanical_hp_proven": False',
            '"manufacturing_authorized": False',
        ):
            self.assertIn(fragment, source)

    def test_workflow_publishes_amd64_digest_attestations_and_anonymous_smoke(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            '"lib3mf" and .versionInfo == "2.5.0"',
            "added_size_bytes",
            "16000000",
            "${{ github.sha }}-vast-f41-cad",
            "steps.build.outputs.digest",
            "Gate anonymous pull of the exact digest",
            "/usr/sbin/sshd -T >/dev/null",
            "runtime_host_keys_generated_before_onstart",
            "noninteractive_ssh_auto_tmux_disabled",
            'DOCKER_CONFIG="${anonymous_config}" docker pull --platform linux/amd64',
            "--user 0:0",
            "--cap-add DAC_OVERRIDE",
            "--cap-add FOWNER",
            "--cap-add SETPCAP",
            "synthetic_step_roundtrip_executed == true",
            "vast_onstart_ready_for_public_archive_transfer_cad_not_started",
            "917-component-factory-f41-vast-ready.json",
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

    def test_no_key_or_private_asset_blob_is_embedded(self):
        private_blob = re.compile(
            r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----\s+[A-Za-z0-9+/=]{40,}",
            re.MULTILINE,
        )
        for path in IMAGE_ROOT.iterdir():
            if not path.is_file():
                continue
            source = path.read_text(encoding="utf-8")
            self.assertIsNone(private_blob.search(source), path.name)
            self.assertNotRegex(source, r"ssh-(?:rsa|ed25519) [A-Za-z0-9+/]{40,}")
            self.assertNotIn("935+Xtreme", source)
            self.assertNotIn("/Users/maxime", source)

    def test_documentation_exposes_exact_wrapper_contract_and_limits(self):
        source = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "runtype: ssh_direct",
            "onstart: /usr/local/bin/917-cad-vast-onstart",
            "ready probe: /workspace/READY",
            "917-cad-stage-job",
            "917-cad-run-job",
            "BUNDLE-MANIFEST.json",
            "run_component_factory_f41_cad_job.sh",
            "jamais depuis le worktree de développement",
            "git show HEAD:<path>",
            "Vast remplace ENTRYPOINT",
            "ssh-keygen -A",
            "sshd.real",
            "/root/.no_auto_tmux",
            "révoqués pour toute nouvelle",
            "66cef346acfd8b3d84e87fa5c53d112ade07d4e183a3e1c00165d6a1c922f70a",
            "component-factory-f41-offers",
            "launch-component-factory-f41 <offer_id>",
            "1,25 USD/h",
            "256 000 Mo de RAM",
            "16 000 000 octets",
            "11 392 378 octets",
            "sha256:dd0a9745badb03a30a795509b442e53ac27675d1ee8f08ef8dfd3498be4b4c16",
            "1 600 ch",
            "https://docs.vast.ai/api-reference/creating-instances-with-api",
            "https://docs.vast.ai/guides/instances/docker-environment",
        ):
            self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
