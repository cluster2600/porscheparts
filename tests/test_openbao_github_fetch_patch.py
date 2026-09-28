"""Offline check of the read-only extension; no credentials or network."""
import importlib.machinery
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class FixedFetchTests(unittest.TestCase):
    def test_fixed_fetch_keeps_scope_and_withholds_failure_diagnostics(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'openbao-github'
            shutil.copyfile(root / 'deploy/openbao/openbao-github', target)
            subprocess.run(['git', 'apply', str(root / 'deploy/openbao/github-fetch-current.patch')], cwd=directory, check=True)
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
