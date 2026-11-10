"""Protect frozen recipes and keep the replacement inventory complete."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "containers/stack-20261105"


class StackRebuildTests(unittest.TestCase):
    def test_results_cover_current_recipes_and_bind_passing_receipts(self):
        rows = json.loads((STACK / "build-results.json").read_text())["images"]
        self.assertEqual({r["name"] for r in rows}, {p.stem for p in STACK.glob("*.Dockerfile")})
        for row in rows:
            with self.subTest(image=row["name"]):
                digest = hashlib.sha256((ROOT / row["recipe"]).read_bytes()).hexdigest()
                self.assertEqual(row["current_recipe_sha256"], digest)
                if row["passed"]:
                    receipt = next(a for a in row["attempts"] if a["receipt"] == row["current_receipt"])
                    self.assertEqual((receipt["build_exit"], receipt["smoke_exit"]), (0, 0))
                    self.assertEqual(receipt["recipe_sha256"].split()[0], digest)

    def test_refresh_rejects_failed_stale_or_missing_smoke_receipts(self):
        for failure in ("build", "smoke", "missing_smoke", "stale_recipe"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copyfile(STACK / "refresh-receipts.py", root / "refresh-receipts.py")
                (root / "fixture.Dockerfile").write_text("FROM scratch\n")
                digest = hashlib.sha256((root / "fixture.Dockerfile").read_bytes()).hexdigest()
                (root / "inventory.json").write_text('{"recipes":[],"recipe_count":0}')
                for number in (1, 2):
                    receipt = root / "receipts" / f"fixture.{number}"
                    receipt.mkdir(parents=True)
                    (receipt / "started.txt").write_text(str(number))
                    (receipt / "recipe.sha256").write_text(
                        ("0" * 64 if failure == "stale_recipe" else digest) + " fixture.Dockerfile")
                    (receipt / "build-exit-code.txt").write_text("1" if number == 2 and failure == "build" else "0")
                    if not (number == 2 and failure == "missing_smoke"):
                        (receipt / "smoke-exit-code.txt").write_text("1" if number == 2 and failure == "smoke" else "0")
                subprocess.run([sys.executable, str(root / "refresh-receipts.py"), str(root / "receipts")],
                               check=True, capture_output=True, text=True)
                row = json.loads((root / "build-results.json").read_text())["images"][0]
                self.assertFalse(row["passed"])
                self.assertEqual(len(row["attempts"]), 2)

    def test_original_recipe_hashes_remain_unchanged(self):
        inventory = json.loads((STACK / "inventory.json").read_text())
        self.assertEqual(inventory["recipe_count"], len(inventory["recipes"]))
        self.assertEqual(len({r["original_recipe"] for r in inventory["recipes"]}), inventory["recipe_count"])
        for row in inventory["recipes"]:
            with self.subTest(recipe=row["original_recipe"]):
                self.assertEqual(hashlib.sha256((ROOT / row["original_recipe"]).read_bytes()).hexdigest(),
                                 row["original_sha256"])

    def test_inventory_covers_existing_recipe_tree(self):
        inventory = json.loads((STACK / "inventory.json").read_text())
        found = set()
        for folder in (ROOT / "containers", ROOT / "twins"):
            for path in folder.rglob("*"):
                if STACK in path.parents or not path.is_file():
                    continue
                if path.name in {"Dockerfile", "Dockerfile.native"} or path.name.endswith(".Dockerfile"):
                    found.add(str(path.relative_to(ROOT)))
        self.assertEqual(found, {r["original_recipe"] for r in inventory["recipes"]})

    def test_copied_topology_program_only_changes_numpy_contract(self):
        original = ROOT / "twins/reference-917-engine/source/build_topology_context_f26.py"
        self.assertEqual((STACK / "build_topology_context_f26.py").read_text(),
                         original.read_text().replace("2.2.6", "2.5.4"))

    def test_python_migration_retains_existing_smoke_assertions(self):
        for name in ("obj-metrology-f15", "boundary-review-f23"):
            with self.subTest(image=name):
                original = (ROOT / "containers" / f"{name}-smoke.py").read_text()
                expected = original.replace("(3, 12)", "(3, 15)").replace("Python 3.12", "Python 3.15")
                self.assertEqual((STACK / f"{name}-smoke.py").read_text(), expected)


if __name__ == "__main__":
    unittest.main()
