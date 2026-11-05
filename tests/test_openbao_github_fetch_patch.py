"""Released openbao-github fetch-current delta (issue #422, owner-approved 2026-11-05).

The repository wrapper stays frozen; the release is the pinned delta applied to
a disposable copy. No credentials or network.
"""
import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE_SHA256 = "100406b0f109a36699c9ffc99062962fb41ea02b15a28802758a3fbf0aed002e"
PATCH_SHA256 = "ed72a944450c7144f92166635d43533d7d15c471f60a1184ee981c9bf99f82e7"
VARIANT_SHA256 = "d94884e66b72acac8753993234727e88748d34fa20566b0a8510403b92732cc9"


class FixedFetchTests(unittest.TestCase):
    def test_fixed_fetch_keeps_scope_and_withholds_failure_diagnostics(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'openbao-github'
            source = root / 'deploy/openbao/openbao-github'
            delta = root / 'deploy/openbao/github-fetch-current.patch'
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), SOURCE_SHA256)
            self.assertEqual(hashlib.sha256(delta.read_bytes()).hexdigest(), PATCH_SHA256)
            shutil.copyfile(source, target)
            subprocess.run(['git', 'apply', str(root / 'deploy/openbao/github-fetch-current.patch')], cwd=directory, check=True)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), VARIANT_SHA256)
            loader = importlib.machinery.SourceFileLoader('fixed_fetch', str(target))
            module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
            loader.exec_module(module)
            self.assertEqual(module.REPOSITORY, 'cluster2600/porscheparts')
            self.assertEqual(module.ALLOWED_SECRET_PATH, 'secrets/data/github')
            result = SimpleNamespace(returncode=0, stdout='', stderr='')
            with patch.object(module, 'current_branch_contract', return_value='codex/test'), patch.object(module.subprocess, 'run', return_value=result) as run:
                module.push_current('test-only-not-a-secret', fetch=True)
                argv = run.call_args.args[0]
                self.assertEqual(argv, ['git', 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main', 'refs/heads/codex/test:refs/remotes/origin/codex/test'])
                self.assertEqual(run.call_args.kwargs['env']['GIT_CONFIG_VALUE_0'], '')
                self.assertNotIn('test-only-not-a-secret', str(argv))
                module.push_current('test-only-not-a-secret')
                self.assertEqual(run.call_args.args[0], ['git', 'push', '--porcelain', 'origin', 'HEAD:refs/heads/codex/test'])
                result.returncode, result.stderr = 1, 'test-only-not-a-secret'
                with self.assertRaisesRegex(module.SafeError, 'diagnostics withheld') as error:
                    module.push_current('test-only-not-a-secret', fetch=True)
                self.assertNotIn(result.stderr, str(error.exception))
