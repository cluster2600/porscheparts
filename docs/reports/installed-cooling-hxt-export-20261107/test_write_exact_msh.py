"""Exercise export identity and fail-closed node matching without loading Gmsh."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np

spec = importlib.util.spec_from_file_location('exact_writer', Path(__file__).with_name('write_exact_msh.py'))
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)

class ExportTests(unittest.TestCase):
    def fake(self, bad=False):
        self.xyz = np.array([[1/3, 1/7, -1/9], [0., 1., 2.]])
        self.tags = np.array([9, 2], dtype=np.uint64)
        self.options = {}
        def save(path):
            rows = ['2 0 1 2', '9 ' + ' '.join(format(x, '.16g') for x in self.xyz[0])]
            if bad:
                rows[-1] = '9 0 0 0'
            self.raw = '$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n2\n' + '\n'.join(rows) + '\n$EndNodes\n$Elements\n0\n$EndElements\n'
            Path(path).write_text(self.raw)
        return SimpleNamespace(option=SimpleNamespace(setNumber=self.options.__setitem__),
            model=SimpleNamespace(mesh=SimpleNamespace(getNodes=lambda: (self.tags, self.xyz.ravel(), []))), write=save)

    def test_exact_values_and_unchanged_other_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'mesh.msh'
            writer.write_exact_msh(self.fake(), out)
            text = out.read_text()
            rows = text.split('$Nodes\n')[1].split('$EndNodes')[0].splitlines()[1:]
            values = {int(row.split()[0]): list(map(float, row.split()[1:])) for row in rows}
            self.assertEqual(values, {int(t): p.tolist() for t, p in zip(self.tags, self.xyz)})
            self.assertNotEqual(text, self.raw)
            self.assertEqual(text.split('$EndNodes')[1], self.raw.split('$EndNodes')[1])
            self.assertEqual(text.split('$Nodes')[0], self.raw.split('$Nodes')[0])
            self.assertEqual(out.with_name('mesh-native16.msh').read_text(), self.raw)
            self.assertEqual(self.options['Mesh.PreserveNumberingMsh2'], 1)

    def test_rejects_mismatched_live_and_exported_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AssertionError):
                writer.write_exact_msh(self.fake(bad=True), Path(tmp)/'mesh.msh')

if __name__ == '__main__':
    unittest.main()
