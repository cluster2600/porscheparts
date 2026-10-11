"""Frozen document exceptions cannot silently accept modified content."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'doc_links', Path(__file__).resolve().parents[1] / 'scripts/check_doc_links.py')
LINKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINKS)


class FrozenDocumentTests(unittest.TestCase):
    def check(self, text, pinned_text=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'README.md').write_text(text)
            subprocess.run(['git', '-C', str(root), 'add', 'README.md'], check=True)
            pins = {} if pinned_text is None else {
                'README.md': hashlib.sha256(pinned_text.encode()).hexdigest()}
            output = io.StringIO()
            with patch.object(LINKS, 'ROOT', root), patch.object(LINKS, 'PINNED_MARKDOWN', pins), \
                    patch('sys.argv', ['check_doc_links.py', '--strict']), contextlib.redirect_stdout(output):
                return LINKS.main(), output.getvalue()

    def test_exact_frozen_document_is_verified_without_rewriting_historical_links(self):
        text = '[Local output](missing.stl)\n'
        code, output = self.check(text, text)
        self.assertEqual(code, 0)
        self.assertIn('1 frozen source(s) hash-verified', output)

    def test_modified_frozen_document_fails_even_when_its_links_are_valid(self):
        code, output = self.check('No links remain.\n', '[Local output](missing.stl)\n')
        self.assertEqual(code, 1)
        self.assertIn('changed pinned source', output)

    def test_ordinary_document_missing_link_still_fails(self):
        code, output = self.check('[Missing output](missing.stl)\n')
        self.assertEqual(code, 1)
        self.assertIn('missing file', output)


if __name__ == '__main__':
    unittest.main()
