import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_container_index as index  # noqa: E402


class ContainerIndexTests(unittest.TestCase):
    def test_every_recipe_is_listed(self):
        text = index.render()
        for recipe in index.recipes():
            rel = recipe.relative_to(ROOT).as_posix()
            self.assertIn(f"(../{rel})", text, rel)

    def test_dockerignore_files_are_not_recipes(self):
        self.assertFalse(any(p.name.endswith(".dockerignore") for p in index.recipes()))

    def test_every_lock_is_matched_to_a_recipe(self):
        text = index.render()
        for name, _, _ in index.lock_records():
            self.assertIn(f"[`{Path(name).name}`]", text, name)

    def test_committed_page_is_current(self):
        self.assertEqual(index.OUTPUT.read_text(encoding="utf-8"), index.render())


if __name__ == "__main__":
    unittest.main()
