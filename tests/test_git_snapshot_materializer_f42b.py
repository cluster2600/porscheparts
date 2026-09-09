"""Tests adversariaux du matérialisateur de snapshot Git F42b."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "deploy/vast/simready/_materialize_git_snapshot.py"
GIT = Path("/usr/bin/git")
PYTHON = Path(sys.executable).resolve()


class GitSnapshotMaterializerF42bTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        self._git(self.repository, "init", "--quiet")
        self._git(self.repository, "config", "user.name", "Snapshot Test")
        self._git(self.repository, "config", "user.email", "snapshot@example.invalid")

        plain = self.repository / "nested/plain.txt"
        executable = self.repository / "bin/run.sh"
        plain.parent.mkdir()
        executable.parent.mkdir()
        self.plain_bytes = b"octets du commit\n"
        self.executable_bytes = b"#!/bin/sh\nprintf 'commit exact\\n'\n"
        plain.write_bytes(self.plain_bytes)
        executable.write_bytes(self.executable_bytes)
        executable.chmod(0o755)
        (self.repository / "plain-link").symlink_to("nested/plain.txt")
        self._git(self.repository, "add", "--", "nested/plain.txt", "bin/run.sh", "plain-link")
        self._git(self.repository, "commit", "--quiet", "-m", "fixture")
        first_revision = self._git_text(self.repository, "rev-parse", "HEAD")
        self._git(
            self.repository,
            "update-index",
            "--add",
            "--cacheinfo",
            "160000",
            first_revision,
            "vendor",
        )
        self._git(self.repository, "commit", "--quiet", "-m", "add gitlink")
        self.revision = self._git_text(self.repository, "rev-parse", "HEAD")

    @staticmethod
    def _clean_environment() -> dict[str, str]:
        return {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("GIT_")
        }

    def _git(self, repository: Path, *arguments: str) -> bytes:
        return subprocess.run(
            [str(GIT), "-C", str(repository), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=self._clean_environment(),
        ).stdout

    def _git_text(self, repository: Path, *arguments: str) -> str:
        return self._git(repository, *arguments).decode("ascii").strip()

    def _run(
        self,
        destination: Path,
        manifest: Path,
        paths: list[str],
        *,
        revision: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        process_environment = os.environ.copy()
        process_environment["PYTHONDONTWRITEBYTECODE"] = "1"
        if environment:
            process_environment.update(environment)
        return subprocess.run(
            [
                str(PYTHON),
                str(HELPER),
                "--repository",
                str(self.repository),
                "--revision",
                revision or self.revision,
                "--destination",
                str(destination),
                "--manifest",
                str(manifest),
                "--",
                *paths,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=self.root,
            env=process_environment,
        )

    def _foreign_repository(self) -> Path:
        repository = self.root / "foreign"
        repository.mkdir()
        self._git(repository, "init", "--quiet")
        self._git(repository, "config", "user.name", "Foreign Test")
        self._git(repository, "config", "user.email", "foreign@example.invalid")
        path = repository / "nested/plain.txt"
        path.parent.mkdir()
        path.write_bytes(b"octets empoisonnes\n")
        self._git(repository, "add", "--", "nested/plain.txt")
        self._git(repository, "commit", "--quiet", "-m", "foreign")
        return repository

    def test_commit_exact_ignore_worktree_index_git_env_et_path(self) -> None:
        (self.repository / "nested/plain.txt").write_bytes(b"mutation worktree\n")
        (self.repository / "bin/run.sh").write_bytes(b"#!/bin/sh\nexit 99\n")
        self._git(self.repository, "add", "--", "nested/plain.txt", "bin/run.sh")

        foreign = self._foreign_repository()
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_marker = self.root / "fake-git-called"
        fake_git = fake_bin / "git"
        fake_git.write_text(
            "#!/bin/sh\n/usr/bin/touch "
            + shlex.quote(str(fake_marker))
            + "\nexit 97\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o755)
        destination = self.root / "snapshot"
        manifest = self.root / "source-allowlist.json"
        result = self._run(
            destination,
            manifest,
            ["nested/plain.txt", "bin/run.sh"],
            environment={
                "PATH": str(fake_bin),
                "GIT_DIR": str(foreign / ".git"),
                "GIT_WORK_TREE": str(foreign),
                "GIT_OBJECT_DIRECTORY": str(foreign / ".git/objects"),
                "GIT_INDEX_FILE": str(foreign / ".git/index"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.bare",
                "GIT_CONFIG_VALUE_0": "true",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(fake_marker.exists())
        self.assertEqual((destination / "nested/plain.txt").read_bytes(), self.plain_bytes)
        self.assertEqual((destination / "bin/run.sh").read_bytes(), self.executable_bytes)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((destination / "nested").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((destination / "bin").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((destination / "nested/plain.txt").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((destination / "bin/run.sh").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o600)

        payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["workflow_profile"], "f42b-six-usd-v1")
        self.assertEqual(payload["source_revision"], self.revision)
        self.assertEqual(payload["git_binary"], str(GIT))
        self.assertEqual(payload["file_count"], 2)
        self.assertEqual(
            payload["total_size_bytes"],
            len(self.plain_bytes) + len(self.executable_bytes),
        )
        expected_bytes = {
            "nested/plain.txt": (self.plain_bytes, "100644", "0600"),
            "bin/run.sh": (self.executable_bytes, "100755", "0700"),
        }
        self.assertEqual([entry["path"] for entry in payload["files"]], list(expected_bytes))
        for entry in payload["files"]:
            data, git_mode, staged_mode = expected_bytes[entry["path"]]
            self.assertEqual(entry["git_mode"], git_mode)
            self.assertEqual(entry["staged_mode"], staged_mode)
            self.assertEqual(entry["size_bytes"], len(data))
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(
                entry["git_blob"],
                self._git_text(
                    self.repository,
                    "rev-parse",
                    f"{self.revision}:{entry['path']}",
                ),
            )

    def test_refuse_revision_courte_et_objet_non_commit(self) -> None:
        for index, revision in enumerate(
            (
                self.revision[:12],
                self._git_text(self.repository, "rev-parse", f"{self.revision}^{{tree}}"),
            )
        ):
            destination = self.root / f"bad-revision-{index}"
            manifest = self.root / f"bad-revision-{index}.json"
            result = self._run(
                destination,
                manifest,
                ["nested/plain.txt"],
                revision=revision,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(destination.exists())
            self.assertFalse(manifest.exists())

    def test_refuse_traversal_et_pathspecs_ambigus_avant_creation(self) -> None:
        unsafe_paths = (
            "../nested/plain.txt",
            "/nested/plain.txt",
            "nested/../plain.txt",
            "./nested/plain.txt",
            "nested//plain.txt",
            "nested\\plain.txt",
            ":(glob)**",
            ".git/config",
            "nested/space name.txt",
        )
        for index, unsafe in enumerate(unsafe_paths):
            with self.subTest(path=unsafe):
                destination = self.root / f"unsafe-{index}"
                manifest = self.root / f"unsafe-{index}.json"
                result = self._run(destination, manifest, [unsafe])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(destination.exists())
                self.assertFalse(manifest.exists())

    def test_refuse_symlink_gitlink_et_repertoire_git(self) -> None:
        for index, relative in enumerate(("plain-link", "vendor", "nested")):
            with self.subTest(path=relative):
                destination = self.root / f"mode-{index}"
                manifest = self.root / f"mode-{index}.json"
                result = self._run(destination, manifest, [relative])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("mode Git interdit", result.stderr)
                self.assertFalse(destination.exists())
                self.assertFalse(manifest.exists())

    def test_refuse_destination_et_manifeste_symlinks_sans_ecraser(self) -> None:
        target = self.root / "target"
        target.mkdir(mode=0o700)
        destination_link = self.root / "snapshot-link"
        destination_link.symlink_to(target, target_is_directory=True)
        first_manifest = self.root / "first.json"
        first = self._run(destination_link, first_manifest, ["nested/plain.txt"])
        self.assertNotEqual(first.returncode, 0)
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse(first_manifest.exists())

        manifest_target = self.root / "manifest-target.json"
        manifest_target.write_text("sentinelle\n", encoding="utf-8")
        manifest_link = self.root / "manifest-link.json"
        manifest_link.symlink_to(manifest_target)
        second_destination = self.root / "second-snapshot"
        second = self._run(
            second_destination,
            manifest_link,
            ["nested/plain.txt"],
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertFalse(second_destination.exists())
        self.assertEqual(manifest_target.read_text(encoding="utf-8"), "sentinelle\n")

    def test_ecrit_exclusivement_sans_suivre_de_symlink(self) -> None:
        source = HELPER.read_text(encoding="utf-8")
        file_flags = "os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW"
        self.assertGreaterEqual(source.count(file_flags), 2)
        destination = self.root / "existing"
        destination.mkdir(mode=0o700)
        sentinel = destination / "sentinel"
        sentinel.write_text("ne pas ecraser\n", encoding="utf-8")
        manifest = self.root / "existing.json"
        result = self._run(destination, manifest, ["nested/plain.txt"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "ne pas ecraser\n")
        self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
