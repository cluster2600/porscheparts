"""Archive recovery checks do not execute or qualify the stored turbo studies."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/bionic-turbo-f1/recovery-20261106"
spec = importlib.util.spec_from_file_location("turbo_recovery", HERE / "recover.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def identity(path):
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class TurboRecoveryTests(unittest.TestCase):
    def test_only_verified_g01_and_scoped_g02_states_advance(self):
        parent_path = ROOT / "twins/bionic-turbo-f1/baseline-20261106-mac/gate-ledger.json"
        parent = json.loads(parent_path.read_text())
        current = json.loads((HERE / "gate-ledger.json").read_text())
        proof = json.loads((HERE / "prerequisites.json").read_text())
        self.assertEqual(hashlib.sha256(parent_path.read_bytes()).hexdigest(), proof["parent_ledger_sha256"])
        self.assertEqual(proof["automation_status"], "PAUSED")
        self.assertFalse(proof["downstream_geometry_solver_and_release_authorized"])
        for old, new in zip(parent["gates"], current["gates"], strict=True):
            if old["id"] == "G02-evidence-recoverable":
                self.assertEqual(new["state"], "engineering_passed")
                continue
            if old["id"] in proof["evaluations"]:
                self.assertEqual(proof["evaluations"][old["id"]], {"may_open": True, "reasons": []})
                self.assertEqual(new["state"], "engineering_passed")
                self.assertEqual(new["receipts"][:-1], old["receipts"])
                new["state"] = old["state"]
                new["receipts"].pop()
            self.assertEqual(old, new)

    def test_recovery_gate_receipts_and_fail_closed_controls(self):
        spec = importlib.util.spec_from_file_location("baseline_recovery_test", HERE.parent / "baseline-20261106/baseline.py")
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        ledger = json.loads((HERE / "gate-ledger.json").read_text())
        matrix = json.loads((HERE.parent / "baseline-20261106-mac/runtime-matrix.json").read_text())
        attestation = json.loads((HERE / "G02-attestation.json").read_text())
        gate = next(g for g in ledger["gates"] if g["id"] == attestation["gate"])
        gate["state"] = "investigated"
        self.assertEqual(baseline.evaluate_gate(gate["id"], ledger, matrix, attestation, ROOT), (True, []))
        proof = json.loads((HERE / "independent-recovery.json").read_text())
        self.assertEqual(proof["source_helper_sha256"], identity(HERE / "recover.py")["sha256"])
        self.assertEqual((proof["checked_files"], proof["archive_packages"]), (96, 2))
        self.assertFalse(proof["geometry_or_solver_executed"])
        key = next(iter(attestation["config_sha256"]))
        attestation["config_sha256"][key] = "0" * 64
        self.assertFalse(baseline.evaluate_gate(gate["id"], ledger, matrix, attestation, ROOT)[0])
        attestation = json.loads((HERE / "G02-attestation.json").read_text())
        ledger["gates"][0]["state"] = "investigated"
        self.assertFalse(baseline.evaluate_gate(gate["id"], ledger, matrix, attestation, ROOT)[0])

    def test_real_manifests_are_pinned_and_ordered(self):
        for name, count, parts in (("contact", 28, 1), ("native", 60, 3)):
            selected, entries = recovery.package(name)
            self.assertEqual(len(entries), count + 1)
            self.assertEqual(entries[-1]["path"], "file-manifest.json")
            self.assertEqual(len(selected["parts"]), parts)
            self.assertEqual(sum(p["bytes"] for p in selected["parts"]), selected["archive"]["bytes"])

    def test_stale_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = json.loads((HERE / "packages.json").read_text())
            manifest["packages"][0]["source_sha256"]["file-manifest.json"] = "0" * 64
            (directory / "packages.json").write_text(json.dumps(manifest))
            with patch.object(recovery, "HERE", directory), self.assertRaisesRegex(ValueError, "stale source manifest"):
                recovery.package("contact")

    def test_reconstruction_and_missing_corrupt_reordered_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "a", root / "b"
            first.write_bytes(b"abc"); second.write_bytes(b"def")
            selected = {"parts": [identity(first), identity(second)], "archive": {"bytes": 6, "sha256": hashlib.sha256(b"abcdef").hexdigest()}}
            recovery.reconstruct(selected, root, root / "joined")
            self.assertEqual((root / "joined").read_bytes(), b"abcdef")
            with self.assertRaises(FileExistsError):
                recovery.reconstruct(selected, root, root / "joined")
            second.rename(root / "missing")
            with self.assertRaises(ValueError):
                recovery.reconstruct(selected, root, root / "missing-output")
            self.assertFalse((root / "missing-output").exists())
            second.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                recovery.reconstruct(selected, root, root / "corrupt-output")
            second.write_bytes(b"def")
            selected["parts"].reverse()
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                recovery.reconstruct(selected, root, root / "wrong-order")

    def test_extract_and_reject_unsafe_members_before_writing(self):
        for kind in ("valid", "escape", "symlink", "duplicate", "missing", "wrong-size"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "trial"; root.mkdir(); archive = root / "archive.tar.gz"
                with tarfile.open(archive, "w:gz") as bundle:
                    if kind != "missing":
                        member = tarfile.TarInfo("../escape" if kind == "escape" else "safe.txt")
                        member.size = 4 if kind == "wrong-size" else 3
                        if kind == "symlink":
                            member.type = tarfile.SYMTYPE; member.linkname = "../escape"
                        bundle.addfile(member, io.BytesIO(b"data" if kind == "wrong-size" else b"abc"))
                        if kind == "duplicate":
                            bundle.addfile(member, io.BytesIO(b"abc"))
                entries = [{"path": "safe.txt", "bytes": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}]
                if kind == "valid":
                    result = recovery.extract(archive, identity(archive), entries, root / "output")
                    self.assertTrue(result["all_payload_sha256_verified"])
                    self.assertEqual((root / "output/safe.txt").read_bytes(), b"abc")
                    link = root / "dangling-link"
                    link.symlink_to(root / "must-not-create")
                    with self.assertRaises(ValueError):
                        recovery.extract(archive, identity(archive), entries, link)
                    self.assertFalse((root / "must-not-create").exists())
                else:
                    with self.assertRaises(ValueError):
                        recovery.extract(archive, identity(archive), entries, root / "output")
                    self.assertFalse((root / "output").exists())
                    self.assertFalse((root.parent / "escape").exists())

    def test_hardlinks_materialise_only_identical_allowlisted_regular_targets(self):
        for kind in ("valid", "external", "wrong-digest", "chain"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); archive = root / "archive.tar.gz"
                with tarfile.open(archive, "w:gz") as bundle:
                    regular = tarfile.TarInfo("original"); regular.size = 3
                    bundle.addfile(regular, io.BytesIO(b"abc"))
                    linked = tarfile.TarInfo("alias"); linked.type = tarfile.LNKTYPE
                    linked.linkname = "../outside" if kind == "external" else "alias" if kind == "chain" else "original"
                    bundle.addfile(linked)
                digest = hashlib.sha256(b"abc").hexdigest()
                entries = [{"path": name, "bytes": 3, "sha256": digest} for name in ("original", "alias")]
                if kind == "wrong-digest":
                    entries[1]["sha256"] = "0" * 64
                if kind == "valid":
                    recovery.extract(archive, identity(archive), entries, root / "output")
                    original, alias = root / "output/original", root / "output/alias"
                    self.assertEqual(alias.read_bytes(), b"abc")
                    self.assertFalse(alias.is_symlink())
                    self.assertNotEqual(original.stat().st_ino, alias.stat().st_ino)
                else:
                    with self.assertRaises(ValueError):
                        recovery.extract(archive, identity(archive), entries, root / "output")
                    self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
