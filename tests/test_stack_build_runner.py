"""Exercise receipt boundaries without building an image or using a registry."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "containers/stack-20261105/build-one.sh"


class StackBuildRunnerTests(unittest.TestCase):
    def test_copy_and_from_parents_are_recorded_before_failed_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "containers/stack-20261105/cad-recode-cad.Dockerfile"
            recipe.parent.mkdir(parents=True)
            recipe.write_text("FROM porscheparts/first:fixture\n"
                              "COPY --from=porscheparts/second:fixture /input /output\n"
                              "COPY --from=porscheparts/first:fixture /input /again\n")
            binaries = root / "bin"
            binaries.mkdir()
            (binaries / "docker").write_text(
                '#!/bin/sh\nif [ "$1 $2" = "image inspect" ]; then\n'
                '  for arg; do :; done\n  printf "%s []\\n" "$arg"\n'
                'else\n  exit 42\nfi\n')
            (binaries / "timeout").write_text('#!/bin/sh\nshift\nexec "$@"\n')
            for path in binaries.iterdir():
                path.chmod(0o755)
            receipts = root / "receipts"
            result = subprocess.run(["bash", str(RUNNER), "cad-recode-cad"], cwd=root,
                                    env={**os.environ, "PATH": f"{binaries}:{os.environ['PATH']}",
                                         "STACK_RECEIPTS": str(receipts),
                                         "STACK_PYTHON_BASE": "porscheparts/python:fixture"},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 42, result.stderr)
            receipt, = receipts.iterdir()
            self.assertEqual((receipt / "local-parent-images.txt").read_text().splitlines(),
                             ["porscheparts/first:fixture []", "porscheparts/second:fixture []"])
            self.assertEqual((receipt / "build-exit-code.txt").read_text().strip(), "42")
            self.assertEqual((receipt / "base-image.txt").read_text().strip(),
                             "porscheparts/python:fixture []")
            self.assertFalse((receipt / "smoke-exit-code.txt").exists())
            self.assertTrue((receipt / "finished.txt").is_file())

    def test_unadmitted_image_is_rejected_before_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            receipts = Path(directory) / "receipts"
            result = subprocess.run(["bash", str(RUNNER), "unadmitted-image"],
                                    env={**os.environ, "STACK_RECEIPTS": str(receipts)},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(receipts.exists())
