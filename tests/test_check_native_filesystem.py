"""Issue #420: make check stops immediately on WSL DrvFs mounts."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_native_filesystem import mount_for, verdict  # noqa: E402

MOUNTINFO = '\n'.join([
    '82 67 8:48 / / rw,relatime - ext4 /dev/sdd rw',
    '78 82 0:34 / /mnt/wsl rw,relatime shared:1 - tmpfs none rw',
    r'131 82 0:69 / /mnt/c rw,noatime - 9p C:\134 rw,aname=drvfs;path=C:\;uid=1000',
    '140 82 0:70 / /mnt/d rw,noatime - drvfs D: rw',
])


class NativeFilesystemTests(unittest.TestCase):
    def test_wsl_drive_mounts_are_refused(self):
        for path in ('/mnt/c/Users/me/porscheparts', '/mnt/c', '/mnt/d/repo'):
            self.assertIsNotNone(verdict(Path(path), MOUNTINFO), path)

    def test_native_paths_pass(self):
        for path in ('/home/me/porscheparts', '/mnt/cdrom/repo', '/mnt/wsl/x'):
            self.assertIsNone(verdict(Path(path), MOUNTINFO), path)
        self.assertEqual(mount_for(Path('/mnt/cdrom'), MOUNTINFO), ('/', 'ext4'))

    def test_cli_exits_nonzero_with_explanation(self):
        with tempfile.NamedTemporaryFile('w', suffix='.mountinfo') as handle:
            handle.write(MOUNTINFO)
            handle.flush()
            run = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/check_native_filesystem.py'),
                 '/mnt/c/repo', '--mountinfo', handle.name],
                capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('Repository location', run.stderr)


if __name__ == '__main__':
    unittest.main()
