"""Issue #416: the private-output guard must stop at the innermost repository.

Agent worktrees live at <checkout>/.claude/worktrees/<id>, where `.git` is a
file. A guard that keeps walking up reaches the outer checkout and rejects the
worktree's own ignored work/ directory.
"""
import hashlib
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
# Guard loops that test every enclosing repository. Each file is hash-pinned by
# a research record, so fixing it in place would break that record's provenance;
# the fix waits on an owner decision to re-run and re-pin (issue #416).
PINNED_ALL_PARENTS_GUARD = {
    'assess_conforming_fea.py', 'audit_interior_relocation.py',
    'prepare_bore_sensitivity.py', 'prepare_conforming_surface.py',
    'run_conforming_study.py', 'run_reconstruction.py',
}
ALL_PARENTS = re.compile(r"/ ?'\.git'\)\.exists\(\) and")


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

    def test_unfixed_guards_are_only_hash_pinned_files(self):
        unfixed = {p.name for p in SOURCE.rglob('*.py') if ALL_PARENTS.search(p.read_text())}
        self.assertEqual(unfixed, PINNED_ALL_PARENTS_GUARD)
        records = '\n'.join(p.read_text() for p in (ROOT / 'docs/research').rglob('*.json'))
        for name in sorted(unfixed):
            digest = hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
            self.assertIn(digest, records, f'{name} is no longer pinned: fix its guard')


if __name__ == '__main__':
    unittest.main()
