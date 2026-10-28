"""Small publication integrity boundary tests; no CAD or scientific imports."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_publication25_integrity',HERE/'verify.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_inventory_requires_exact_set_size_and_full_hash(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t).resolve();p=root/'payload';p.write_text('frozen');files={'payload':dict(bytes=p.stat().st_size,sha256=m.sha(p))};m.check_inventory(root,files)
            (root/'extra').touch()
            with self.assertRaisesRegex(ValueError,'set differs'):m.check_inventory(root,files)
            (root/'extra').unlink();p.write_text('change')
            with self.assertRaisesRegex(ValueError,'SHA differs'):m.check_inventory(root,files)
    def test_inventory_refuses_symlink_and_keeps_eleven_status_keys(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t).resolve();target=root/'target';target.write_text('same');(root/'link').symlink_to(target)
            files={n:dict(bytes=(root/n).stat().st_size,sha256=m.sha(root/n))for n in ['target','link']}
            with self.assertRaisesRegex(ValueError,'Symlink'):m.check_inventory(root,files)
        self.assertEqual(len(m.KEYS),11);self.assertEqual(m.KEYS[0],'status')
if __name__=='__main__':unittest.main()
