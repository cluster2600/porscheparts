"""Issue #416: the private-output guard must stop at the innermost repository.

Agent worktrees live at <checkout>/.claude/worktrees/<id>, where `.git` is a
file. A guard that keeps walking up reaches the outer checkout and rejects the
worktree's own ignored work/ directory.
"""
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
from photo_guided_surface_repair import require_private_output  # noqa: E402

GIT = '.git'
# Owner decision 2026-11-05: the six hash-pinned scripts that kept the
# all-parents loop were fixed and re-pinned by a dated record; no source may
# reintroduce the loop.
ALL_PARENTS = re.compile(r"/ ?'\.git'\)\.exists\(\) and")
REPIN = ROOT / 'docs/research/935-horizontal-cooling/source-repin-20261105.json'


class NestedWorktreeGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.outer = Path(temp.name) / 'checkout'
        (self.outer / GIT).mkdir(parents=True)
        self.worktree = self.outer / '.claude' / 'worktrees' / 'agent'
        self.worktree.mkdir(parents=True)
        (self.worktree / GIT).write_text('gitdir: ../../../.git/worktrees/agent\n')

    def test_nested_worktree_work_dir_is_accepted(self):
        require_private_output(self.worktree / 'work' / 'run')

    def test_nested_worktree_tracked_path_is_rejected(self):
        with self.assertRaises(ValueError):
            require_private_output(self.worktree / 'docs' / 'run')

    def test_no_source_keeps_the_all_parents_guard(self):
        unfixed = {p.name for p in SOURCE.rglob('*.py') if ALL_PARENTS.search(p.read_text())}
        self.assertEqual(unfixed, set())


class SourceRepinRecordTests(unittest.TestCase):
    def test_repin_changes_only_the_guard_and_keeps_history_verifiable(self):
        record = json.loads(REPIN.read_text())
        self.assertEqual(record['issue'], 416)
        self.assertIs(record['results_recomputed'], False)
        self.assertEqual(len(record['sources']), 6)
        for path, entry in record['sources'].items():
            text = (ROOT / path).read_text()
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), entry['current_sha256'], path)
            swap = entry['guard_replacement']
            self.assertEqual(text.count(swap['current']), 1, path)
            self.assertIn("'.git'", swap['historical'])
            historical = text.replace(swap['current'], swap['historical'])
            self.assertEqual(hashlib.sha256(historical.encode()).hexdigest(), entry['historical_sha256'], path)
        for path, entry in record['unchanged_sources'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), entry['sha256'], path)

    def test_historical_records_still_name_the_historical_hashes(self):
        record = json.loads(REPIN.read_text())
        texts = '\n'.join((ROOT / p).read_text() for p in record['historical_records_unchanged'])
        for path, entry in record['sources'].items():
            self.assertIn(entry['historical_sha256'], texts, path)
            self.assertNotIn(entry['current_sha256'], texts, path)


if __name__ == '__main__':
    unittest.main()
