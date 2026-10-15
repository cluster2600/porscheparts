import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT/'twins/993-intercooler'
LINK = re.compile(r'\]\(([^)#\s]+)\)')


class IntercoolerHubTests(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        for page in [HUB/'README.md', *HUB.glob('750-hp/**/README.md'), ROOT/'twins/README.md', ROOT/'twins/993-installed-cooling-f1/README.md']:
            for target in LINK.findall(page.read_text(encoding='utf-8')):
                if target.startswith(('http://', 'https://')): continue
                self.assertTrue((page.parent/target).exists(), f'{page.relative_to(ROOT)} -> {target}')

    def test_old_locations_are_gone(self):
        self.assertFalse((ROOT/'twins/993-installed-cooling-f1/intercooler-750').exists())
        self.assertFalse((ROOT/'twins/993-intercooler-bracket-ti-f0').exists())

    def test_overview_is_drawn_from_retained_results(self):
        o = json.loads((HUB/'derived/overview.json').read_text())
        for path, digest in o['source_sha256'].items(): self.assertEqual(hashlib.sha256((HUB/path).read_bytes()).hexdigest(), digest, path)
        self.assertEqual(o['status'], 'review_figure_not_evidence')


if __name__ == '__main__':
    unittest.main()
