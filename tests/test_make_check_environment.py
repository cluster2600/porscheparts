"""Keep Make recipes on the project interpreter, including macOS Make 3.81."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CheckEnvironmentTests(unittest.TestCase):
    def test_recipe_uses_project_python_without_shell_activation(self):
        makefile = Path(__file__).resolve().parents[1] / "Makefile"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            python = root / ".venv-check/bin/python3"
            python.parent.mkdir(parents=True)
            python.symlink_to(sys.executable)
            probe = root / "probe.mk"
            probe.write_text("runtime-proof:\n\t@python3 -c 'import sys; print(sys.executable)'\n")
            result = subprocess.run(
                ["make", "-s", "-f", str(makefile), "-f", str(probe), "runtime-proof"],
                cwd=root, capture_output=True, text=True, check=True,
            )
            self.assertEqual(Path(result.stdout.strip()), python)


if __name__ == "__main__":
    unittest.main()
